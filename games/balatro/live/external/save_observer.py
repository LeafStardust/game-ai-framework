from __future__ import annotations

from typing import Any

from games.balatro.live.protocol import LiveBalatroSnapshot

from .save_state import BalatroSaveReader, BalatroSaveSnapshot


SAVE_PHASES = {
    1: "SELECTING_HAND",
    5: "SHOP",
    7: "BLIND_SELECT",
    8: "ROUND_EVAL",
}

STAKE_NAMES = {
    1: "WHITE",
    2: "RED",
    3: "GREEN",
    4: "BLACK",
    5: "BLUE",
    6: "PURPLE",
    7: "ORANGE",
    8: "GOLD",
}


class SaveBalatroObserver:

    def __init__(self, reader: BalatroSaveReader | None = None):
        self.reader = reader or BalatroSaveReader()
        self._sequence = 0
        self._last_sha256: str | None = None

    def observe(self) -> LiveBalatroSnapshot:
        save = self.reader.read()
        if save.sha256 != self._last_sha256:
            self._sequence += 1
            self._last_sha256 = save.sha256
        return snapshot_from_save(save, sequence=self._sequence)

    def is_connected(self) -> bool:
        try:
            self.reader.read(retries=1, retry_delay=0)
        except (OSError, RuntimeError):
            return False
        return True


def snapshot_from_save(
    save: BalatroSaveSnapshot,
    *,
    sequence: int = 1,
) -> LiveBalatroSnapshot:
    data = _mapping(save.data)
    game = _mapping(data.get("GAME"))
    blind = _mapping(data.get("BLIND"))
    back = _mapping(data.get("BACK"))
    round_resets = _mapping(game.get("round_resets"))
    current_round = _mapping(game.get("current_round"))
    areas = _mapping(data.get("cardAreas"))

    state_id = _integer(data.get("STATE"), -1)
    phase = SAVE_PHASES.get(state_id, f"SAVE_STATE_{state_id}")
    stake_id = _integer(game.get("stake"), 1)

    hand = _normalize_area(areas, "hand")
    deck = _normalize_area(areas, "deck")
    consumables = _normalize_area(areas, "consumeables", "consumables")
    jokers = _normalize_area(areas, "jokers")
    play = _normalize_area(areas, "play")
    discard = _normalize_area(areas, "discard")

    payload: dict[str, Any] = {
        "money": _integer(game.get("dollars"), 0),
        "ante_num": _integer(round_resets.get("ante"), 1),
        "round_num": _integer(game.get("round"), 1),
        "deck": _deck_name(back, game),
        "stake": STAKE_NAMES.get(stake_id, str(stake_id)),
        "round": {
            "chips": _integer(blind.get("chips"), 0),
            "hands_left": _integer(current_round.get("hands_left"), 0),
            "discards_left": _integer(current_round.get("discards_left"), 0),
        },
        "score": _integer(game.get("chips"), 0),
        "hand": hand,
        "cards": deck,
        "consumables": consumables,
        "jokers": jokers,
        "play": play,
        "discard": discard,
        "hands": _mapping(game.get("hands")),
        "blind": _normalize_blind(blind, game),
        "won": bool(game.get("won", False)),
        "save_state": state_id,
        "save_path": str(save.path),
        "save_modified_ns": save.modified_ns,
        "save_sha256": save.sha256,
        "raw_save": data,
    }

    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=False,
        payload=payload,
    )


def _normalize_area(
    areas: dict[Any, Any],
    name: str,
    *aliases: str,
) -> dict[str, Any]:
    area = {}
    for candidate in (name, *aliases):
        area = _mapping(areas.get(candidate))
        if area:
            break

    config = _mapping(area.get("config"))
    cards = _ordered_values(area.get("cards"))
    return {
        "count": _integer(config.get("card_count"), len(cards)),
        "limit": _integer(config.get("card_limit"), len(cards)),
        "cards": [_normalize_card(card) for card in cards],
        "raw": area,
    }


def _normalize_card(card: dict[Any, Any]) -> dict[str, Any]:
    base = _mapping(card.get("base"))
    save_fields = _mapping(card.get("save_fields"))
    value = base.get("value")
    suit = base.get("suit")
    center = save_fields.get("center")

    modifier: dict[str, Any] = {}
    if isinstance(center, str) and center.startswith("m_"):
        modifier["enhancement"] = center

    edition = _edition_name(card.get("edition"))
    if edition is not None:
        modifier["edition"] = edition

    seal = card.get("seal")
    if isinstance(seal, str) and seal:
        modifier["seal"] = seal.upper()

    return {
        "value": {
            "rank": value,
            "suit": suit,
        },
        "modifier": modifier,
        "live_id": card.get("playing_card", card.get("sort_id")),
        "center": center,
        "debuff": bool(card.get("debuff", False)),
        "raw": card,
    }


def _normalize_blind(blind: dict[Any, Any], game: dict[Any, Any]) -> dict[str, Any]:
    blind_on_deck = str(game.get("blind_on_deck", "Small"))
    if bool(blind.get("boss", False)) or blind_on_deck.upper() == "BOSS":
        blind_type = "BOSS"
    elif blind_on_deck.upper() == "BIG":
        blind_type = "BIG"
    else:
        blind_type = "SMALL"

    return {
        "type": blind_type,
        "status": "CURRENT" if bool(game.get("facing_blind", False)) else "SELECT",
        "name": blind.get("name"),
        "score": _integer(blind.get("chips"), 0),
        "key": blind.get("config_blind"),
        "raw": blind,
    }


def _deck_name(back: dict[Any, Any], game: dict[Any, Any]) -> str:
    key = back.get("key")
    if not isinstance(key, str):
        selected = _mapping(game.get("selected_back_key"))
        key = selected.get("key")
    if isinstance(key, str) and key.startswith("b_"):
        return key[2:].upper()

    name = back.get("name")
    if isinstance(name, str) and name:
        return name.removesuffix(" Deck").upper()
    return "BASE"


def _edition_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.upper()
    if not isinstance(value, dict):
        return None
    for name in ("negative", "polychrome", "holo", "foil"):
        if value.get(name):
            return name.upper()
    return None


def _ordered_values(value: Any) -> list[dict[Any, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []

    def sort_key(key: Any) -> tuple[int, Any]:
        if isinstance(key, int) and not isinstance(key, bool):
            return 0, key
        return 1, str(key)

    return [
        value[key]
        for key in sorted(value, key=sort_key)
        if isinstance(value[key], dict)
    ]


def _mapping(value: Any) -> dict[Any, Any]:
    return value if isinstance(value, dict) else {}


def _integer(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
