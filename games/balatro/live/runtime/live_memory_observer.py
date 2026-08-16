from __future__ import annotations

import hashlib
import json
from typing import Any

from games.balatro.live.joker_state_reader import declared_joker_state_specs
from games.balatro.live.protocol import LiveBalatroSnapshot

from .balatro_g_discovery import discover_balatro_g_table
from .luajit_memory import LuaJITMemoryError, LuaValue
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder
from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader
from .save_observer import STAKE_NAMES


class LiveMemoryObservationError(RuntimeError):
    pass


class LiveMemoryBalatroObserver:
    """Authoritative read-only observer for the currently running Balatro VM.

    Only explicitly whitelisted live fields are exposed. The observer never
    serializes ``G``/``G.GAME`` recursively and therefore never exposes the
    game's PRNG state or ordered future draw pile. ``G.deck.cards`` is reduced
    to an unordered public remaining-deck composition, while ``G.playing_cards``
    is independently canonicalized as the public permanent owned-deck composition.
    """

    def __init__(
        self,
        reader: WindowsProcessMemoryReader | None = None,
        decoder: LuaJITNonGC64Decoder | None = None,
        g_table: int | None = None,
    ) -> None:
        self.reader = reader
        self.decoder = decoder
        self._g_table = g_table
        self._owns_reader = reader is None and decoder is None
        self._sequence = 0
        self._last_fingerprint: str | None = None

    def _connect(self) -> None:
        if self.decoder is not None:
            return
        if self.reader is None:
            self.reader = WindowsProcessMemoryReader.from_balatro_window()
        self.decoder = LuaJITNonGC64Decoder(self.reader)

    def _root(self) -> tuple[LuaJITNonGC64Decoder, int, dict[str, LuaValue]]:
        self._connect()
        assert self.decoder is not None

        if self._g_table is None:
            self._g_table = discover_balatro_g_table(self.decoder)

        try:
            root = self.decoder.string_fields(self._g_table)
        except (BalatroProcessMemoryError, LuaJITMemoryError) as error:
            self._g_table = None
            raise LiveMemoryObservationError(
                f"unable to read cached Balatro G table: {error}"
            ) from error

        required = ("GAME", "STATE", "STATES", "hand", "jokers", "deck")
        if not all(name in root for name in required):
            # A VM restart can invalidate the cached table address. Rediscover once.
            self._g_table = discover_balatro_g_table(self.decoder)
            root = self.decoder.string_fields(self._g_table)
            if not all(name in root for name in required):
                missing = ", ".join(name for name in required if name not in root)
                raise LiveMemoryObservationError(
                    "live Balatro G table is missing required fields: " + missing
                )

        return self.decoder, self._g_table, root

    def observe(self) -> LiveBalatroSnapshot:
        decoder, _, root = self._root()
        payload, phase, state_complete = snapshot_payload_from_live_memory(
            decoder,
            root,
        )

        fingerprint_source = {
            "phase": phase,
            "state_complete": state_complete,
            "payload": payload,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_source,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if fingerprint != self._last_fingerprint:
            self._sequence += 1
            self._last_fingerprint = fingerprint

        return LiveBalatroSnapshot(
            sequence=self._sequence,
            phase=phase,
            state_complete=state_complete,
            payload=payload,
        )

    def is_connected(self) -> bool:
        try:
            self._root()
        except (OSError, RuntimeError):
            return False
        return True

    def close(self) -> None:
        if self._owns_reader and self.reader is not None:
            self.reader.close()
        self.reader = None
        self.decoder = None
        self._g_table = None

    def __enter__(self) -> "LiveMemoryBalatroObserver":
        self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def snapshot_payload_from_live_memory(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
) -> tuple[dict[str, Any], str, bool]:
    game = _table_fields(decoder, root.get("GAME"))
    current_round = _table_fields(decoder, game.get("current_round"))
    round_resets = _table_fields(decoder, game.get("round_resets"))
    blind = _table_fields(decoder, game.get("blind"))

    phase = _phase_name(decoder, root)
    state_complete = _boolean(root.get("STATE_COMPLETE"), False)
    stake_id = _integer(game.get("stake"), 1)
    round_joker_state = _normalize_round_joker_public_state(decoder, current_round)
    blind_tags = _normalize_blind_tags(decoder, round_resets.get("blind_tags"))
    normalized_blind = _normalize_blind(decoder, blind, game)
    current_tag = blind_tags.get(str(normalized_blind.get("type") or "").lower())
    if current_tag:
        normalized_blind["tag"] = current_tag

    hand = _normalize_area(decoder, root.get("hand"), preserve_order=True)
    jokers = _normalize_item_area(
        decoder,
        root.get("jokers"),
        preserve_index=False,
        public_state_by_center=round_joker_state,
    )
    consumables = _normalize_item_area(
        decoder,
        root.get("consumeables"),
        preserve_index=True,
    )

    # The live deck table is physically ordered by future draw order. We may
    # inspect its members to recover public remaining-deck composition, but the
    # agent-facing snapshot is canonical-sorted before exposure.
    deck = _normalize_area(decoder, root.get("deck"), preserve_order=False)

    # G.playing_cards is the public permanent playing-card collection. Its internal
    # array order is not strategically meaningful, so expose only a canonicalized
    # composition. Keep absence distinct from an authoritative empty collection.
    playing_cards = root.get("playing_cards")
    owned_deck = (
        _normalize_card_array(decoder, playing_cards)
        if playing_cards is not None and playing_cards.kind == "table"
        else None
    )

    shop_jokers = _normalize_item_area(
        decoder,
        root.get("shop_jokers"),
        preserve_index=True,
        public_state_by_center=round_joker_state,
    )
    shop_boosters = _normalize_item_area(
        decoder,
        root.get("shop_booster"),
        preserve_index=True,
    )
    shop_vouchers = _normalize_item_area(
        decoder,
        root.get("shop_vouchers"),
        preserve_index=True,
    )

    payload: dict[str, Any] = {
        "money": _integer(game.get("dollars"), 0),
        "ante_num": _integer(round_resets.get("ante"), 1),
        "round_num": _integer(game.get("round"), 1),
        "deck": _deck_name(decoder, game),
        "stake": STAKE_NAMES.get(stake_id, str(stake_id)),
        "last_tarot_planet": _string(game.get("last_tarot_planet")),
        "round": {
            "chips": _integer(blind.get("chips"), 0),
            "hands_left": _integer(current_round.get("hands_left"), 0),
            "discards_left": _integer(current_round.get("discards_left"), 0),
            "discards_used": _integer(current_round.get("discards_used"), 0),
        },
        "score": _integer(game.get("chips"), 0),
        "hand": hand,
        "cards": deck,
        "jokers": jokers,
        "consumables": consumables,
        "shop_jokers": shop_jokers,
        "shop_boosters": shop_boosters,
        "shop_vouchers": shop_vouchers,
        "hands": _normalize_hand_levels(decoder, game.get("hands")),
        "blind": normalized_blind,
        "won": _boolean(game.get("won"), False),
        "live_state_source": "process_memory",
        "hidden_rng_exposed": False,
        "hidden_draw_order_exposed": False,
    }
    if owned_deck is not None:
        payload["owned_cards"] = owned_deck

    return payload, phase, state_complete


def _table_fields(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, LuaValue]:
    if value is None or value.kind != "table":
        return {}
    try:
        return decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError):
        return {}


def _array_table_values(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> list[tuple[int, int]]:
    if value is None or value.kind != "table":
        return []
    try:
        items = decoder.array_items(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError):
        return []
    return [
        (index, int(item.value))
        for index, item in items
        if item.kind == "table"
    ]


def _phase_name(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
) -> str:
    state = root.get("STATE")
    states = root.get("STATES")
    if state is None or states is None or states.kind != "table":
        return "UNKNOWN"
    if state.kind not in {"integer", "number"}:
        return "UNKNOWN"

    target = int(state.value)
    for name, value in decoder.string_fields(int(states.value)).items():
        if value.kind in {"integer", "number"} and int(value.value) == target:
            return name
    return f"STATE_{target}"


def _normalize_area(
    decoder: LuaJITNonGC64Decoder,
    area_value: LuaValue | None,
    *,
    preserve_order: bool,
) -> dict[str, Any]:
    area = _table_fields(decoder, area_value)
    config = _table_fields(decoder, area.get("config"))
    cards_value = area.get("cards")
    raw_cards = _array_table_values(decoder, cards_value)
    cards = [_normalize_card(decoder, address) for _, address in raw_cards]

    if not preserve_order:
        cards.sort(key=_public_card_sort_key)

    return {
        "count": len(cards),
        "limit": _integer(config.get("card_limit"), len(cards)),
        "cards": cards,
    }


def _normalize_card_array(
    decoder: LuaJITNonGC64Decoder,
    cards_value: LuaValue | None,
) -> dict[str, Any]:
    cards = [
        _normalize_card(decoder, address)
        for _, address in _array_table_values(decoder, cards_value)
    ]
    cards.sort(key=_public_card_sort_key)
    return {
        "count": len(cards),
        "limit": len(cards),
        "cards": cards,
    }


def _normalize_item_area(
    decoder: LuaJITNonGC64Decoder,
    area_value: LuaValue | None,
    *,
    preserve_index: bool,
    public_state_by_center: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    area = _table_fields(decoder, area_value)
    config = _table_fields(decoder, area.get("config"))
    raw_cards = _array_table_values(decoder, area.get("cards"))
    cards = [
        _normalize_item(
            decoder,
            address,
            area_index=(position if preserve_index else None),
            public_state_by_center=public_state_by_center,
        )
        for position, (_, address) in enumerate(raw_cards)
    ]
    return {
        "count": len(cards),
        "limit": _integer(config.get("card_limit"), len(cards)),
        "cards": cards,
    }


def _normalize_card(
    decoder: LuaJITNonGC64Decoder,
    address: int,
) -> dict[str, Any]:
    card = decoder.string_fields(address)
    base = _table_fields(decoder, card.get("base"))
    ability = _table_fields(decoder, card.get("ability"))
    config = _table_fields(decoder, card.get("config"))
    center = _table_fields(decoder, config.get("center"))

    modifier: dict[str, Any] = {}
    center_key = _string(center.get("key"))
    if center_key and center_key.startswith("m_"):
        modifier["enhancement"] = center_key

    edition = _edition_name(decoder, card.get("edition"))
    if edition is not None:
        modifier["edition"] = edition

    seal = _string(card.get("seal"))
    if seal:
        modifier["seal"] = seal.upper()

    result: dict[str, Any] = {
        "value": {
            "rank": _primitive(base.get("value")),
            "suit": _string(base.get("suit")),
        },
        "modifier": modifier,
        "live_id": _first_primitive(
            card.get("playing_card"),
            card.get("sort_id"),
            card.get("ID"),
        ),
        "center": center_key,
        "debuff": _boolean(card.get("debuff"), False),
        "permanent_bonus": _integer(ability.get("perma_bonus"), 0),
        "label": _first_string(card.get("label"), center.get("name")),
    }

    geometry = _geometry(decoder, card.get("T"))
    if geometry:
        result["ui"] = geometry
    return result


def _normalize_item(
    decoder: LuaJITNonGC64Decoder,
    address: int,
    *,
    area_index: int | None,
    public_state_by_center: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    card = decoder.string_fields(address)
    ability = _table_fields(decoder, card.get("ability"))
    config = _table_fields(decoder, card.get("config"))
    center = _table_fields(decoder, config.get("center"))

    ability_name = _string(ability.get("name"))
    center_name = _string(center.get("name"))
    label = _first_string(card.get("label"), ability.get("name"), center.get("name"))
    ability_set = _first_string(ability.get("set"), center.get("set"))
    center_key = _string(center.get("key"))

    result: dict[str, Any] = {
        "live_id": _first_primitive(
            card.get("sort_id"),
            card.get("playing_card"),
            card.get("ID"),
        ),
        "center": center_key,
        "label": label,
        "ability_name": ability_name or center_name,
        "ability_set": ability_set,
        "debuff": _boolean(card.get("debuff"), False),
    }
    rarity = _rarity_name(center.get("rarity"))
    if rarity is not None:
        result["rarity"] = rarity
    if area_index is not None:
        result["area_index"] = area_index

    edition = _edition_name(decoder, card.get("edition"))
    if edition is not None:
        result["edition"] = edition

    for field in ("cost", "sell_cost"):
        value = _number(card.get(field))
        if value is not None:
            result[field] = value

    public_state = _normalize_public_item_state(
        decoder,
        center_key,
        label,
        ability_name,
        ability,
        card,
    )
    if center_key and public_state_by_center:
        public_state.update(public_state_by_center.get(center_key, {}))
    if public_state:
        result["public_state"] = public_state

    geometry = _geometry(decoder, card.get("T"))
    if geometry:
        result["ui"] = geometry
    return result


def _normalize_public_item_state(
    decoder: LuaJITNonGC64Decoder,
    center_key: str | None,
    label: str | None,
    ability_name: str | None,
    ability: dict[str, LuaValue],
    card: dict[str, LuaValue],
) -> dict[str, Any]:
    """Read only explicitly declared primitive state for one modeled Joker."""
    specs = declared_joker_state_specs(
        center=center_key,
        label=label,
        ability_name=ability_name,
    )
    if not specs:
        return {}

    extra_value = ability.get("extra")
    extra = _table_fields(decoder, extra_value)
    result: dict[str, Any] = {}

    for spec in specs:
        value = None
        for key in spec.ability_keys:
            value = _primitive(ability.get(key))
            if value is None:
                value = _primitive(extra.get(key))
            if value is not None:
                break

        if value is None:
            for key in spec.card_keys:
                value = _primitive(card.get(key))
                if value is not None:
                    break

        if value is None and spec.scalar_extra:
            value = _primitive(extra_value)

        if value is not None:
            result[spec.model_field] = value

    return result


def _normalize_round_joker_public_state(
    decoder: LuaJITNonGC64Decoder,
    current_round: dict[str, LuaValue],
) -> dict[str, dict[str, Any]]:
    """Read only visible per-round targets used by dynamic Jokers."""
    result: dict[str, dict[str, Any]] = {}

    ancient_card = _table_fields(decoder, current_round.get("ancient_card"))
    ancient_suit = _string(ancient_card.get("suit"))
    if ancient_suit:
        result["j_ancient"] = {"suit": ancient_suit}

    castle_card = _table_fields(decoder, current_round.get("castle_card"))
    castle_suit = _string(castle_card.get("suit"))
    if castle_suit:
        result["j_castle"] = {"suit": castle_suit}

    idol_card = _table_fields(decoder, current_round.get("idol_card"))
    idol_rank = _string(idol_card.get("rank"))
    idol_suit = _string(idol_card.get("suit"))
    if idol_rank and idol_suit:
        result["j_idol"] = {
            "rank": idol_rank,
            "suit": idol_suit,
        }

    mail_card = _table_fields(decoder, current_round.get("mail_card"))
    mail_rank = _string(mail_card.get("rank"))
    if mail_rank:
        result["j_mail"] = {"rank": mail_rank}

    return result


def _normalize_hand_levels(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, dict[str, int]]:
    if value is None or value.kind != "table":
        return {}
    result: dict[str, dict[str, int]] = {}
    for name, hand_value in decoder.string_fields(int(value.value)).items():
        if hand_value.kind != "table":
            continue
        hand = _table_fields(decoder, hand_value)
        result[name] = {
            "level": _integer(hand.get("level"), 1),
            "played": _integer(hand.get("played"), 0),
            "played_this_round": _integer(hand.get("played_this_round"), 0),
        }
    return result


def _normalize_blind_tags(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, str]:
    """Expose only the public Small/Big skip-tag keys for the current ante."""
    tags = _table_fields(decoder, value)
    result: dict[str, str] = {}
    for live_key in ("Small", "Big"):
        tag = _string(tags.get(live_key))
        if tag:
            result[live_key.lower()] = tag
    return result


def _normalize_blind(
    decoder: LuaJITNonGC64Decoder,
    blind: dict[str, LuaValue],
    game: dict[str, LuaValue],
) -> dict[str, Any]:
    blind_on_deck = (_string(game.get("blind_on_deck")) or "Small").upper()
    boss = _boolean(blind.get("boss"), False) or blind_on_deck == "BOSS"
    if boss:
        blind_type = "BOSS"
    elif blind_on_deck == "BIG":
        blind_type = "BIG"
    else:
        blind_type = "SMALL"

    config = _table_fields(decoder, blind.get("config"))
    blind_config = _table_fields(decoder, config.get("blind"))
    key = _first_string(
        blind.get("config_blind"),
        blind_config.get("key"),
        config.get("key"),
    )

    result: dict[str, Any] = {
        "type": blind_type,
        "status": "CURRENT" if _boolean(game.get("facing_blind"), False) else "SELECT",
        "name": _first_string(blind.get("name"), blind_config.get("name")),
        "score": _integer(blind.get("chips"), 0),
        "key": key,
    }

    # The Eye and The Mouth keep ordinary public round state on the active Blind
    # object. Expose only those whitelisted fields; never serialize Blind recursively.
    hands_value = blind.get("hands")
    if hands_value is not None and hands_value.kind == "table":
        hands = _table_fields(decoder, hands_value)
        result["hands"] = sorted(
            name
            for name, value in hands.items()
            if _boolean(value, False)
        )

    only_hand_value = blind.get("only_hand")
    if only_hand_value is not None:
        # Mouth initializes this field to false. Preserve key presence while
        # normalizing false/non-string to None so the translator knows it was read.
        result["only_hand"] = _string(only_hand_value)

    return result


def _deck_name(
    decoder: LuaJITNonGC64Decoder,
    game: dict[str, LuaValue],
) -> str:
    for value in (game.get("selected_back_key"), game.get("selected_back")):
        if value is None:
            continue
        if value.kind == "string":
            key = str(value.value)
            if key.startswith("b_"):
                return key[2:].upper()
            if key:
                return key.removesuffix(" Deck").upper()
        if value.kind == "table":
            back = _table_fields(decoder, value)
            key = _first_string(back.get("key"), back.get("name"))
            if key:
                if key.startswith("b_"):
                    return key[2:].upper()
                return key.removesuffix(" Deck").upper()

    return "BASE"


def _rarity_name(value: LuaValue | None) -> str | None:
    rarity = _primitive(value)
    if isinstance(rarity, bool) or rarity is None:
        return None
    if isinstance(rarity, (int, float)):
        return {
            1: "COMMON",
            2: "UNCOMMON",
            3: "RARE",
            4: "LEGENDARY",
        }.get(int(rarity))
    if isinstance(rarity, str):
        normalized = rarity.strip().upper()
        if normalized.isdigit():
            return {
                1: "COMMON",
                2: "UNCOMMON",
                3: "RARE",
                4: "LEGENDARY",
            }.get(int(normalized))
        if normalized in {"COMMON", "UNCOMMON", "RARE", "LEGENDARY"}:
            return normalized
    return None


def _edition_name(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> str | None:
    if value is None:
        return None
    if value.kind == "string":
        return str(value.value).upper()
    if value.kind != "table":
        return None
    edition = _table_fields(decoder, value)
    for name in ("negative", "polychrome", "holo", "foil"):
        if _boolean(edition.get(name), False):
            return name.upper()
    return None


def _geometry(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, float]:
    table = _table_fields(decoder, value)
    result: dict[str, float] = {}
    for field in ("x", "y", "w", "h", "r", "scale"):
        number = _number(table.get(field))
        if number is not None:
            result[field] = float(number)
    return result


def _public_card_sort_key(card: dict[str, Any]) -> tuple[str, ...]:
    value = card.get("value") or {}
    modifier = card.get("modifier") or {}
    return (
        str(value.get("suit") or ""),
        str(value.get("rank") or ""),
        str(modifier.get("enhancement") or ""),
        str(modifier.get("edition") or ""),
        str(modifier.get("seal") or ""),
        str(card.get("permanent_bonus") or ""),
        str(card.get("live_id") or ""),
    )


def _primitive(value: LuaValue | None) -> Any:
    if value is None:
        return None
    if value.kind in {"string", "integer", "number", "boolean"}:
        return value.value
    return None


def _number(value: LuaValue | None) -> int | float | None:
    if value is None or value.kind not in {"integer", "number"}:
        return None
    return value.value


def _integer(value: LuaValue | None, default: int) -> int:
    number = _number(value)
    return int(number) if number is not None else default


def _boolean(value: LuaValue | None, default: bool) -> bool:
    if value is None or value.kind != "boolean":
        return default
    return bool(value.value)


def _string(value: LuaValue | None) -> str | None:
    if value is None or value.kind != "string":
        return None
    return str(value.value)


def _first_primitive(*values: LuaValue | None) -> Any:
    for value in values:
        primitive = _primitive(value)
        if primitive is not None:
            return primitive
    return None


def _first_string(*values: LuaValue | None) -> str | None:
    for value in values:
        text = _string(value)
        if text:
            return text
    return None
