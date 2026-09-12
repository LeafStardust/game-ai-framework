"""Versioned fixed-shape policy observations for the promoted Red/White surface."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable, TYPE_CHECKING

from games.balatro.card import EDITIONS, ENHANCEMENTS, SEALS, BalatroCard
from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
)
from games.balatro.env.joker_centers import VANILLA_JOKER_CENTERS
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.tag_selection import ALL_TAG_KEYS
from games.balatro.env.voucher_capabilities import SHOP_BASE_GENERATION_VOUCHER_KEYS
from games.balatro.hand import PokerHand
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.planets import PLANET_CARDS
from games.balatro.spectrals import SPECTRAL_CARDS
from games.balatro.tarots import TAROT_CARDS
from games.balatro.state import BalatroState

if TYPE_CHECKING:
    from games.balatro.env.state import EnvStateFrame


PUBLIC_OBSERVATION_VERSION = "balatro-red-white-public-observation-v1"

PHASES = (
    "ROUND_START", "BLIND_SELECT", "DRAW_TO_HAND", "SELECTING_HAND", "SHOP",
    "BUFFOON_PACK", "PLANET_PACK", "SPECTRAL_PACK", "STANDARD_PACK", "TAROT_PACK",
)
STATUSES = ("RUNNING", "ANTE_8_WIN", "LOSS")
OWNERS = ("AGENT", "TACTICAL_POLICY", "ENVIRONMENT", "TERMINAL")
BLIND_TYPES = ("SMALL", "BIG", "BOSS")
BOSS_NAMES = (
    "The Psychic", "The Eye", "The Mouth", "The Club", "The Goad", "The Window",
    "The Plant", "The Pillar", "The Head", "The House", "The Wheel", "The Fish",
    "The Mark", "Amber Acorn", "Verdant Leaf", "Crimson Heart", "Cerulean Bell",
)
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
HAND_KEYS = tuple(hand.value for hand in PokerHand)
ENHANCEMENT_ORDER = tuple(sorted(ENHANCEMENTS))
EDITION_ORDER = tuple(sorted(EDITIONS))
SEAL_ORDER = tuple(sorted(SEALS))
TAG_KEYS = tuple(sorted(ALL_TAG_KEYS))
VOUCHER_KEYS = tuple(sorted(SHOP_BASE_GENERATION_VOUCHER_KEYS))
JOKER_CENTER_KEYS = tuple(center.key for center in VANILLA_JOKER_CENTERS)
CONSUMABLE_CENTER_KEYS = (*VANILLA_TAROT_CENTER_ORDER, *VANILLA_PLANET_CENTER_ORDER)
PACK_CENTER_KEYS = tuple(
    f"p_{family}_{size}_{variant}"
    for family in ("arcana", "celestial", "standard", "buffoon", "spectral")
    for size, variants in (("normal", range(1, 5)), ("jumbo", range(1, 3)), ("mega", range(1, 3)))
    for variant in variants
)

MAX_HAND_CARDS = 22
MAX_OWNED_CARDS = 52
MAX_DISCARD_CARDS = 52
MAX_JOKERS = 6
MAX_CONSUMABLES = 3
MAX_SHOP_JOKERS = 3
MAX_SHOP_CONSUMABLES = 3
MAX_SHOP_BOOSTERS = 2
MAX_SHOP_VOUCHERS = 1

_JOKER_STATE_FIELDS = (
    "active", "chip_mod", "chips", "destroyed", "discarded_cards", "hand_size",
    "hands", "mult", "rank", "rounds", "rounds_remaining", "sell_value", "suit",
    "target_hand", "x_mult",
)
_JOKER_METADATA_FIELDS = (
    "center", "center_key", "label", "rarity", "edition", "base_cost", "cost",
    "sell_cost", "discovered", "eternal", "debuffed", "live_id", "area_index",
)
_JOKER_CLASS_TO_CENTER: dict[str, str] = {}
_factory = LiveJokerFactory()
for _center in VANILLA_JOKER_CENTERS:
    _class = _factory.resolve_class({"center": _center.key})
    if _class is not None:
        _JOKER_CLASS_TO_CENTER[_class.__name__] = _center.key
_JOKER_CLASS_TO_CENTER.update({
    "GluttonousJoker": "j_gluttenous_joker", "JokerStencil": "j_stencil",
    "ChaosTheClownJoker": "j_chaos", "DelayedGratificationJoker": "j_delayed_grat",
    "BusinessCardJoker": "j_business", "ToDoListJoker": "j_todo_list",
    "GiftCardJoker": "j_gift", "MailInRebateJoker": "j_mail",
    "BaseballCardJoker": "j_baseball", "TradingCardJoker": "j_trading",
    "FlashCardJoker": "j_flash", "SpareTrousersJoker": "j_trousers",
    "SeltzerJoker": "j_selzer", "SmileyFaceJoker": "j_smiley",
    "GoldenTicketJoker": "j_ticket", "ShowmanJoker": "j_ring_master",
    "OopsAll6sJoker": "j_oops", "CanioJoker": "j_caino",
})


class PublicObservationEncodingError(ValueError):
    """Raised instead of emitting a partial or lossy policy observation."""


@dataclass(frozen=True)
class PublicObservationSchema:
    version: str
    feature_names: tuple[str, ...]

    @property
    def shape(self) -> tuple[int]:
        return (len(self.feature_names),)


@dataclass(frozen=True)
class EncodedPublicObservation:
    schema_version: str
    values: tuple[float, ...]

    @property
    def shape(self) -> tuple[int]:
        return (len(self.values),)


def _slot_names(prefix: str, count: int, fields: Iterable[str]) -> list[str]:
    return [f"{prefix}.{index}.{field}" for index in range(count) for field in fields]


_CARD_FIELDS = (
    "present", "rank", "suit", "enhancement", "edition", "seal", "debuffed",
    "permanent_bonus", "forced_selection", "face_down", "facing_observed",
    "played_this_ante", "played_this_ante_observed", "original_suit_nominal",
)
_JOKER_FIELDS = (
    "present", "center", "edition", "debuffed", "rarity", "base_cost", "cost",
    "sell_cost", "discovered", "eternal",
    *tuple(value for field in _JOKER_STATE_FIELDS for value in (f"{field}.present", field)),
)
_CONSUMABLE_FIELDS = (
    "present", "center", "category", "hand_type", "chips", "mult", "price", "discovered",
)
_SHOP_ITEM_FIELDS = ("present", "center", "kind", "rarity", "edition", "base_cost", "price", "discovered")


def _build_feature_names() -> tuple[str, ...]:
    names = [
        "frame.status", "frame.owner", "state.phase", "state.money", "state.ante",
        "state.round", "state.score", "state.blind_score", "state.blind.present",
        "state.blind.type", "state.blind.requirement", "state.blind.reward",
        "state.blind.disabled", "state.blind.tag", "state.shop_active",
        "state.boss_name", "state.boss_blind_state_observed", "state.boss_blind_only_hand",
        "state.round_most_played_hand", "state.last_played_hand", "state.last_tarot_planet",
        "state.deck_remaining", "state.hand_size", "state.ectoplasm_hand_size_penalty",
        "state.hands_remaining", "state.discards_remaining",
        "state.discards_used.present", "state.discards_used", "state.joker_slots",
        "state.consumable_slots", "state.glass_cards_destroyed",
        "state.round_reset_hands_observed", "state.round_reset_hands",
        "state.round_reset_discards_observed", "state.round_reset_discards",
        "state.vouchers_observed", "state.interest_cap_observed", "state.interest_cap",
        "state.shop_inflation_observed", "state.shop_inflation",
        "state.shop_discount_percent_observed", "state.shop_discount_percent",
        "state.joker_generation_pool_observed", "state.consumable_generation_pool_observed",
        "state.voucher_generation_pool_observed", "state.joker_generation_edition_rate",
        "state.tarot_rate", "state.planet_rate",
    ]
    for prefix in ("level", "plays", "round_plays", "boss_played", "visible"):
        names.extend(f"hands.{prefix}.{hand}" for hand in HAND_KEYS)
    names.extend(f"vouchers.owned.{key}" for key in VOUCHER_KEYS)
    names.extend(_slot_names("hand", MAX_HAND_CARDS, _CARD_FIELDS))
    names.extend(_slot_names("owned_deck", MAX_OWNED_CARDS, _CARD_FIELDS))
    names.extend(_slot_names("discard", MAX_DISCARD_CARDS, _CARD_FIELDS))
    names.extend(_slot_names("jokers", MAX_JOKERS, _JOKER_FIELDS))
    names.extend(_slot_names("consumables", MAX_CONSUMABLES, _CONSUMABLE_FIELDS))
    names.extend(_slot_names("shop.jokers", MAX_SHOP_JOKERS, _SHOP_ITEM_FIELDS))
    names.extend(_slot_names("shop.consumables", MAX_SHOP_CONSUMABLES, _SHOP_ITEM_FIELDS))
    names.extend(_slot_names("shop.boosters", MAX_SHOP_BOOSTERS, _SHOP_ITEM_FIELDS))
    names.extend(_slot_names("shop.vouchers", MAX_SHOP_VOUCHERS, _SHOP_ITEM_FIELDS))
    names.extend(f"pool.joker.{key}" for key in JOKER_CENTER_KEYS)
    names.extend(f"pool.consumable.{key}" for key in CONSUMABLE_CENTER_KEYS)
    names.extend(f"pool.voucher.{key}" for key in VOUCHER_KEYS)
    return tuple(names)


PUBLIC_OBSERVATION_SCHEMA = PublicObservationSchema(PUBLIC_OBSERVATION_VERSION, _build_feature_names())


def _index(value: Any, allowed: tuple[str, ...], field: str, *, optional: bool = False) -> float:
    if optional and value is None:
        return 0.0
    raw = getattr(value, "value", value)
    if not isinstance(raw, str) or raw not in allowed:
        raise PublicObservationEncodingError(f"{field} is outside the versioned schema: {raw!r}")
    return float(allowed.index(raw) + 1)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise PublicObservationEncodingError(f"{field} must be a finite number")
    return float(value)


def _boolean(value: Any, field: str) -> float:
    if not isinstance(value, bool):
        raise PublicObservationEncodingError(f"{field} must be boolean")
    return float(value)


def _rarity(value: Any, field: str) -> float:
    if isinstance(value, str):
        normalized = value.strip().upper()
        names = {"COMMON": 1, "UNCOMMON": 2, "RARE": 3, "LEGENDARY": 4}
        if normalized in names:
            return float(names[normalized])
    number = _number(value, field)
    if number not in (1.0, 2.0, 3.0, 4.0):
        raise PublicObservationEncodingError(f"{field} must be a vanilla rarity")
    return number


def _card_values(card: BalatroCard | None, field: str) -> list[float]:
    if card is None:
        return [0.0] * len(_CARD_FIELDS)
    if not isinstance(card, BalatroCard):
        raise PublicObservationEncodingError(f"{field} contains a non-BalatroCard")
    hidden = card.face_down
    rank_allowed = ("?", *RANKS) if hidden else RANKS
    suit_allowed = ("?", *SUITS) if hidden else SUITS
    if hidden and any((card.live_id is not None, card.enhancement is not None, card.edition is not None,
                       card.seal is not None, card.debuffed, card.permanent_bonus != 0,
                       card.played_this_ante, card.played_this_ante_observed,
                       card.original_suit_nominal is not None)):
        raise PublicObservationEncodingError(f"{field} face-down identity was not fully masked")
    original = -1.0 if card.original_suit_nominal is None else _number(card.original_suit_nominal, f"{field}.original_suit_nominal")
    return [
        1.0, _index(card.rank, rank_allowed, f"{field}.rank"),
        _index(card.suit, suit_allowed, f"{field}.suit"),
        _index(card.enhancement, ENHANCEMENT_ORDER, f"{field}.enhancement", optional=True),
        _index(card.edition, EDITION_ORDER, f"{field}.edition", optional=True),
        _index(card.seal, SEAL_ORDER, f"{field}.seal", optional=True),
        _boolean(card.debuffed, f"{field}.debuffed"), _number(card.permanent_bonus, f"{field}.permanent_bonus"),
        _boolean(card.forced_selection, f"{field}.forced_selection"), _boolean(card.face_down, f"{field}.face_down"),
        _boolean(card.facing_observed, f"{field}.facing_observed"), _boolean(card.played_this_ante, f"{field}.played_this_ante"),
        _boolean(card.played_this_ante_observed, f"{field}.played_this_ante_observed"), original,
    ]


def _fixed_cards(cards: Any, capacity: int, field: str, *, canonical: bool = False) -> list[float]:
    if not isinstance(cards, list):
        raise PublicObservationEncodingError(f"{field} must be a list")
    if len(cards) > capacity:
        raise PublicObservationEncodingError(f"{field} exceeds schema capacity {capacity}")
    ordered = list(cards)
    if canonical:
        ordered.sort(key=lambda card: tuple(_card_values(card, field)[1:]))
    values: list[float] = []
    for index in range(capacity):
        values.extend(_card_values(ordered[index] if index < len(ordered) else None, f"{field}[{index}]"))
    return values


def _joker_center(joker: Any, field: str) -> str:
    center = getattr(joker, "center_key", None) or getattr(joker, "center", None)
    if center is None:
        center = _JOKER_CLASS_TO_CENTER.get(type(joker).__name__)
    if center not in JOKER_CENTER_KEYS:
        raise PublicObservationEncodingError(f"{field} Joker identity is not pinned")
    return center


def _joker_values(joker: Any | None, field: str) -> list[float]:
    if joker is None:
        return [0.0] * len(_JOKER_FIELDS)
    if not hasattr(joker, "__dict__"):
        raise PublicObservationEncodingError(f"{field} Joker identity is not pinned")
    unknown = set(vars(joker)) - set(_JOKER_STATE_FIELDS) - set(_JOKER_METADATA_FIELDS)
    if unknown:
        raise PublicObservationEncodingError(f"{field} has unsupported public state field {sorted(unknown)[0]!r}")
    result = [
        1.0, _index(_joker_center(joker, field), JOKER_CENTER_KEYS, f"{field}.center"),
        _index(getattr(joker, "edition", None), EDITION_ORDER, f"{field}.edition", optional=True),
        _boolean(bool(getattr(joker, "debuffed", False)), f"{field}.debuffed"),
    ]
    for name in ("rarity", "base_cost", "cost", "sell_cost"):
        value = getattr(joker, name, None)
        result.append(-1.0 if value is None else (_rarity(value, f"{field}.{name}") if name == "rarity" else _number(value, f"{field}.{name}")))
    for name in ("discovered", "eternal"):
        value = getattr(joker, name, None)
        result.append(-1.0 if value is None else _boolean(value, f"{field}.{name}"))
    for name in _JOKER_STATE_FIELDS:
        if not hasattr(joker, name):
            result.extend((0.0, 0.0))
            continue
        value = getattr(joker, name)
        if name == "rank": encoded = _index(value, RANKS, f"{field}.{name}")
        elif name == "suit": encoded = _index(value, SUITS, f"{field}.{name}")
        elif name == "target_hand": encoded = _index(value, HAND_KEYS, f"{field}.{name}")
        elif isinstance(value, bool): encoded = float(value)
        else: encoded = _number(value, f"{field}.{name}")
        result.extend((1.0, encoded))
    return result


def _fixed_jokers(items: Any, capacity: int, field: str) -> list[float]:
    if not isinstance(items, list) or len(items) > capacity:
        raise PublicObservationEncodingError(f"{field} must fit schema capacity {capacity}")
    values: list[float] = []
    for index in range(capacity):
        values.extend(_joker_values(items[index] if index < len(items) else None, f"{field}[{index}]"))
    return values


def _consumable_center(item: Any, field: str) -> str:
    center = getattr(item, "center_key", None) or getattr(item, "center", None)
    if center in CONSUMABLE_CENTER_KEYS:
        return center
    name = getattr(item, "name", None)
    for key, value in PLANET_CARDS.items():
        if value.name == name:
            return f"c_{key.lower()}"
    names = {key: getattr(value, "name", None) for key, value in TAROT_CARDS.items()}
    names.update({key: getattr(value, "name", None) for key, value in SPECTRAL_CARDS.items()})
    for key, candidate in names.items():
        if candidate == name:
            center = "c_" + str(key).lower().replace(" ", "_")
            if center in CONSUMABLE_CENTER_KEYS:
                return center
    raise PublicObservationEncodingError(f"{field} consumable identity is not pinned")


def _consumable_values(item: Any | None, field: str) -> list[float]:
    if item is None:
        return [0.0] * len(_CONSUMABLE_FIELDS)
    category = str(getattr(item, "category", getattr(item, "card_type", ""))).upper()
    category_id = _index(category, ("TAROT", "PLANET"), f"{field}.category")
    hand_type = getattr(item, "hand_type", None)
    return [1.0, _index(_consumable_center(item, field), CONSUMABLE_CENTER_KEYS, f"{field}.center"), category_id,
            _index(hand_type, HAND_KEYS, f"{field}.hand_type", optional=True),
            _number(getattr(item, "chips", 0), f"{field}.chips"), _number(getattr(item, "mult", 0), f"{field}.mult"),
            _number(getattr(item, "price", 3), f"{field}.price"),
            -1.0 if getattr(item, "discovered", None) is None else _boolean(item.discovered, f"{field}.discovered")]


def _fixed_consumables(items: Any, capacity: int, field: str) -> list[float]:
    if not isinstance(items, list) or len(items) > capacity:
        raise PublicObservationEncodingError(f"{field} must fit schema capacity {capacity}")
    values: list[float] = []
    for index in range(capacity):
        values.extend(_consumable_values(items[index] if index < len(items) else None, f"{field}[{index}]"))
    return values


def _shop_values(item: Any | None, field: str, centers: tuple[str, ...], kind: str) -> list[float]:
    if item is None:
        return [0.0] * len(_SHOP_ITEM_FIELDS)
    center = getattr(item, "center_key", None) or getattr(item, "center", None)
    actual_kind = str(getattr(item, "kind", kind)).upper()
    if kind == "CONSUMABLE":
        actual_kind = "CONSUMABLE"
    return [1.0, _index(center, centers, f"{field}.center"),
            _index(actual_kind, ("JOKER", "CONSUMABLE", "BOOSTER", "VOUCHER"), f"{field}.kind"),
            -1.0 if getattr(item, "rarity", None) is None else _rarity(item.rarity, f"{field}.rarity"),
            _index(getattr(item, "edition", None), EDITION_ORDER, f"{field}.edition", optional=True),
            -1.0 if getattr(item, "base_cost", None) is None else _number(item.base_cost, f"{field}.base_cost"),
            _number(getattr(item, "price", getattr(item, "cost", None)), f"{field}.price"),
            -1.0 if getattr(item, "discovered", None) is None else _boolean(item.discovered, f"{field}.discovered")]


def _fixed_shop(items: Any, capacity: int, field: str, centers: tuple[str, ...], kind: str) -> list[float]:
    if not isinstance(items, list) or len(items) > capacity:
        raise PublicObservationEncodingError(f"{field} must fit schema capacity {capacity}")
    values: list[float] = []
    for index in range(capacity):
        values.extend(_shop_values(items[index] if index < len(items) else None, f"{field}[{index}]", centers, kind))
    return values


def _pool_mask(observed: bool, pools: Any, keys: tuple[str, ...], field: str) -> list[float]:
    if not observed:
        if pools not in ({}, []):
            raise PublicObservationEncodingError(f"{field} data exists without observation authority")
        return [0.0] * len(keys)
    records = [record for group in pools.values() for record in group] if isinstance(pools, dict) else pools
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise PublicObservationEncodingError(f"{field} must contain exact records")
    record_keys = [record.get("key") for record in records]
    if any(key not in keys for key in record_keys) or len(record_keys) != len(set(record_keys)):
        raise PublicObservationEncodingError(f"{field} contains unknown or duplicate centers")
    return [1.0 if key in record_keys else 0.0 for key in keys]


def encode_public_observation(frame: "EnvStateFrame") -> EncodedPublicObservation:
    """Encode one frame without consulting seed, RNG, draw order, or live ids."""
    from games.balatro.env.state import EnvStateFrame
    if not isinstance(frame, EnvStateFrame):
        raise TypeError("frame must be EnvStateFrame")
    state = public_observation_state(frame.state)
    if state.deck_name != "RED" or state.stake_name != "WHITE":
        raise PublicObservationEncodingError("schema supports Red Deck / White Stake only")
    if state.owned_deck is None:
        raise PublicObservationEncodingError("owned_deck authority is required")
    if not isinstance(state.deck, list):
        raise PublicObservationEncodingError("remaining deck must be a list")
    blind = state.blind
    if blind is not None and getattr(blind, "modifiers", []):
        raise PublicObservationEncodingError("blind modifiers are not represented by this schema")
    values = [
        _index(frame.status, STATUSES, "frame.status"), _index(frame.owner, OWNERS, "frame.owner"),
        _index(state.phase, PHASES, "state.phase"), _number(state.money, "state.money"),
        _number(state.ante, "state.ante"), _number(state.round, "state.round"), _number(state.score, "state.score"),
        _number(state.blind_score, "state.blind_score"), float(blind is not None),
        _index(getattr(blind, "type", None), BLIND_TYPES, "state.blind.type", optional=True),
        _number(getattr(blind, "requirement", 0), "state.blind.requirement"),
        _number(getattr(blind, "reward", 0), "state.blind.reward"),
        _boolean(bool(getattr(blind, "disabled", False)), "state.blind.disabled"),
        _index(getattr(blind, "tag_key", None), TAG_KEYS, "state.blind.tag", optional=True),
        _boolean(state.shop_active, "state.shop_active"),
        _index(state.boss_name, BOSS_NAMES, "state.boss_name", optional=True),
        _boolean(state.boss_blind_state_observed, "state.boss_blind_state_observed"),
        _index(state.boss_blind_only_hand, HAND_KEYS, "state.boss_blind_only_hand", optional=True),
        _index(state.round_most_played_hand, HAND_KEYS, "state.round_most_played_hand", optional=True),
        _index(state.last_played_hand, HAND_KEYS, "state.last_played_hand", optional=True),
        _index(state.last_tarot_planet, tuple(TAROT_CARDS) + tuple(card.name for card in PLANET_CARDS.values()), "state.last_tarot_planet", optional=True),
        _number(len(state.deck), "state.deck_remaining"),
        _number(state.hand_size, "state.hand_size"),
        _number(state.ectoplasm_hand_size_penalty, "state.ectoplasm_hand_size_penalty"),
        _number(state.hands_remaining, "state.hands_remaining"), _number(state.discards_remaining, "state.discards_remaining"),
        float(state.discards_used is not None), 0.0 if state.discards_used is None else _number(state.discards_used, "state.discards_used"),
        _number(state.joker_slots, "state.joker_slots"), _number(state.consumable_slots, "state.consumable_slots"),
        _number(state.glass_cards_destroyed, "state.glass_cards_destroyed"),
        _boolean(state.round_reset_hands_observed, "state.round_reset_hands_observed"), _number(state.round_reset_hands, "state.round_reset_hands"),
        _boolean(state.round_reset_discards_observed, "state.round_reset_discards_observed"), _number(state.round_reset_discards, "state.round_reset_discards"),
        _boolean(state.vouchers_observed, "state.vouchers_observed"), _boolean(state.interest_cap_observed, "state.interest_cap_observed"),
        _number(state.interest_cap, "state.interest_cap"), _boolean(state.shop_inflation_observed, "state.shop_inflation_observed"),
        _number(state.shop_inflation, "state.shop_inflation"), _boolean(state.shop_discount_percent_observed, "state.shop_discount_percent_observed"),
        _number(state.shop_discount_percent, "state.shop_discount_percent"),
        _boolean(state.joker_generation_pool_observed, "state.joker_generation_pool_observed"),
        _boolean(state.consumable_generation_pool_observed, "state.consumable_generation_pool_observed"),
        _boolean(state.voucher_generation_pool_observed, "state.voucher_generation_pool_observed"),
        _number(state.joker_generation_edition_rate, "state.joker_generation_edition_rate"),
        _number(state.tarot_rate, "state.tarot_rate"), _number(state.planet_rate, "state.planet_rate"),
    ]
    mappings = (state.hand_levels, state.hand_play_counts, state.round_hand_play_counts)
    for mapping, label in zip(mappings, ("levels", "plays", "round plays")):
        if not isinstance(mapping, dict) or set(mapping) != set(HAND_KEYS):
            raise PublicObservationEncodingError(f"{label} must cover the exact poker-hand catalogue")
        values.extend(_number(mapping[key], f"{label}.{key}") for key in HAND_KEYS)
    if not isinstance(state.boss_blind_hands, set) or not state.boss_blind_hands.issubset(HAND_KEYS):
        raise PublicObservationEncodingError("Boss hand history contains an unknown hand")
    values.extend(float(key in state.boss_blind_hands) for key in HAND_KEYS)
    visible = set(state.visible_poker_hands)
    if not visible.issubset(HAND_KEYS):
        raise PublicObservationEncodingError("visible poker hands contain an unknown hand")
    values.extend(float(key in visible) for key in HAND_KEYS)
    if not isinstance(state.vouchers, list) or len(state.vouchers) != len(set(state.vouchers)) or any(key not in VOUCHER_KEYS for key in state.vouchers):
        raise PublicObservationEncodingError("owned Vouchers are not an exact supported set")
    values.extend(float(key in state.vouchers) for key in VOUCHER_KEYS)
    values.extend(_fixed_cards(state.hand, MAX_HAND_CARDS, "hand"))
    values.extend(_fixed_cards(state.owned_deck, MAX_OWNED_CARDS, "owned_deck", canonical=True))
    values.extend(_fixed_cards(state.discard_pile, MAX_DISCARD_CARDS, "discard", canonical=True))
    values.extend(_fixed_jokers(state.jokers, MAX_JOKERS, "jokers"))
    values.extend(_fixed_consumables(state.consumables, MAX_CONSUMABLES, "consumables"))
    values.extend(_fixed_shop(state.shop_jokers, MAX_SHOP_JOKERS, "shop.jokers", JOKER_CENTER_KEYS, "JOKER"))
    values.extend(_fixed_shop(state.shop_consumables, MAX_SHOP_CONSUMABLES, "shop.consumables", CONSUMABLE_CENTER_KEYS, "CONSUMABLE"))
    values.extend(_fixed_shop(state.shop_boosters, MAX_SHOP_BOOSTERS, "shop.boosters", PACK_CENTER_KEYS, "BOOSTER"))
    values.extend(_fixed_shop(state.shop_vouchers, MAX_SHOP_VOUCHERS, "shop.vouchers", VOUCHER_KEYS, "VOUCHER"))
    values.extend(_pool_mask(state.joker_generation_pool_observed, state.joker_generation_pools, JOKER_CENTER_KEYS, "Joker pool"))
    values.extend(_pool_mask(state.consumable_generation_pool_observed, state.consumable_generation_pools, CONSUMABLE_CENTER_KEYS, "consumable pool"))
    values.extend(_pool_mask(state.voucher_generation_pool_observed, state.voucher_generation_pool, VOUCHER_KEYS, "Voucher pool"))
    encoded = EncodedPublicObservation(PUBLIC_OBSERVATION_VERSION, tuple(values))
    if encoded.shape != PUBLIC_OBSERVATION_SCHEMA.shape:
        raise RuntimeError("public observation implementation drifted from its versioned schema")
    return encoded
