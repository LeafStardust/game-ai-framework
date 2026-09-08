from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import (
    component_contribution,
    finalize_development,
    state_contribution,
)
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.mechanics import (
    ADD_SEALED_CARD,
    ADD_STONE_CARD,
    CONTAINS_PAIR_CHIPS,
    CONTAINS_PAIR_MULT,
    CONTAINS_PAIR_XMULT,
    CONTAINS_THREE_CHIPS,
    CONTAINS_THREE_MULT,
    CONTAINS_THREE_XMULT,
    DUPLICATE_SELECTED_CARD,
    FLUSH_CHIPS,
    FLUSH_MULT,
    FLUSH_XMULT,
    FOUR_CARD_HAND_SCALING,
    FOUR_CARD_STRAIGHT_FLUSH,
    FOUR_KIND_XMULT,
    RETRIGGER_FINAL_HAND,
    RETRIGGER_FIRST_SCORED,
    RETRIGGER_PLAYED_FACE,
    RETRIGGER_PLAYED_LOW_RANK,
    SCALE_ON_CARD_ADDED,
    SMALL_HAND_CHIPS,
    SMALL_HAND_MULT,
    STRAIGHT_CHIPS,
    STRAIGHT_GAP_RELAXATION,
    STRAIGHT_MULT,
    STRAIGHT_SCALING,
    STRAIGHT_XMULT,
    SUIT_MERGE_RED_BLACK,
    TWO_PAIR_CHIPS,
    TWO_PAIR_MULT,
    TWO_PAIR_SCALING,
    component_has_mechanic,
)

HAND_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}
FOUR_KIND_THRESHOLDS = {**HAND_THRESHOLDS, BondRank.R5: 25.0}
FULL_HOUSE_THRESHOLDS = {**HAND_THRESHOLDS, BondRank.R5: 22.0}
FLUSH_HOUSE_THRESHOLDS = {**HAND_THRESHOLDS, BondRank.R5: 23.0}
PLAYED_RETRIGGER_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 14.0,
    BondRank.R4: 21.0,
    BondRank.R5: 29.0,
}
DECK_GROWTH_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 7.0,
    BondRank.R3: 12.0,
    BondRank.R4: 18.0,
    BondRank.R5: 25.0,
}


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    return list(owned) if owned is not None else list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    result = 0.0
    for threshold, score in bands:
        if value < threshold:
            break
        result = score
    return result


def _level_score(level: int) -> float:
    if level <= 1:
        return 0.0
    if level <= 3:
        return 1.0
    if level <= 6:
        return 3.0
    if level <= 10:
        return 5.0
    if level <= 15:
        return 8.0
    if level <= 24:
        return 12.0
    return 18.0


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return fallback if cls in {"str", "SimpleNamespace"} else cls


def _hand_level(state: Any, hand: str) -> int:
    return int((getattr(state, "hand_levels", {}) or {}).get(hand, 1) or 1)


def _append_mechanic(
    parts: list[BondContribution],
    component: Any,
    index: int,
    mechanic: str,
    value: float,
    label: str,
) -> None:
    if component_has_mechanic(component, mechanic):
        parts.append(component_contribution(
            component,
            collection="jokers",
            index=index,
            label=_source(component, label),
            value=value,
            mechanic=mechanic,
        ))


def _hand_bond(
    state: Any,
    bond_id: str,
    hand: str,
    mechanic_weights: tuple[tuple[str, float, str], ...],
    thresholds: dict[BondRank, float] = HAND_THRESHOLDS,
) -> BondDevelopment:
    parts: list[BondContribution] = []
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        for mechanic, value, label in mechanic_weights:
            _append_mechanic(parts, joker, index, mechanic, value, label)
    level = _level_score(_hand_level(state, hand))
    if level:
        parts.append(state_contribution(
            f"hand_level:{hand}",
            f"{hand} permanent hand level",
            level,
            mechanic="permanent_hand_level",
        ))
    return finalize_development(bond_id, parts, thresholds, target=hand)


def evaluate_pair_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "pair", "PAIR", (
        (CONTAINS_PAIR_XMULT, 6.0, "Pair XMult payoff"),
        (CONTAINS_PAIR_MULT, 4.0, "Pair Mult payoff"),
        (CONTAINS_PAIR_CHIPS, 4.0, "Pair Chips payoff"),
        (SMALL_HAND_MULT, 2.0, "Small-hand Mult"),
    ))


def evaluate_high_card_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "high_card", "HIGH_CARD", (
        (SMALL_HAND_CHIPS, 6.0, "Small-hand Chips"),
        (SMALL_HAND_MULT, 3.0, "Small-hand Mult"),
    ))


def evaluate_two_pair_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "two_pair", "TWO_PAIR", (
        (TWO_PAIR_SCALING, 7.0, "Two-pair scaling"),
        (FOUR_CARD_HAND_SCALING, 3.0, "Four-card hand scaling"),
        (CONTAINS_PAIR_MULT, 2.0, "Pair Mult payoff"),
        (CONTAINS_PAIR_CHIPS, 2.0, "Pair Chips payoff"),
        (TWO_PAIR_MULT, 4.0, "Two-pair Mult"),
        (TWO_PAIR_CHIPS, 4.0, "Two-pair Chips"),
    ))


def evaluate_three_kind_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "three_kind", "THREE_OF_A_KIND", (
        (CONTAINS_THREE_XMULT, 6.0, "Three-kind XMult payoff"),
        (CONTAINS_THREE_MULT, 4.0, "Three-kind Mult payoff"),
        (CONTAINS_THREE_CHIPS, 4.0, "Three-kind Chips payoff"),
    ))


def evaluate_four_kind_bond(state: Any) -> BondDevelopment:
    return _hand_bond(
        state,
        "four_kind",
        "FOUR_OF_A_KIND",
        ((FOUR_KIND_XMULT, 7.0, "Four-kind XMult payoff"),),
        FOUR_KIND_THRESHOLDS,
    )


def evaluate_straight_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "straight", "STRAIGHT", (
        (STRAIGHT_XMULT, 6.0, "Straight XMult payoff"),
        (STRAIGHT_MULT, 4.0, "Straight Mult payoff"),
        (STRAIGHT_CHIPS, 4.0, "Straight Chips payoff"),
        (STRAIGHT_GAP_RELAXATION, 5.0, "Straight gap relaxation"),
        (FOUR_CARD_STRAIGHT_FLUSH, 3.0, "Four-card straight support"),
        (STRAIGHT_SCALING, 4.0, "Straight scaling"),
    ))


def _flush_density(state: Any) -> float:
    smeared = any(
        component_has_mechanic(joker, SUIT_MERGE_RED_BLACK)
        for joker in list(getattr(state, "jokers", ()) or ())
    )
    suits: dict[str, int] = {}
    for card in _deck(state):
        enhancement = str(getattr(card, "enhancement", "") or "").lower()
        if bool(getattr(card, "is_stone", False)) or enhancement == "stone":
            continue
        suit = str(getattr(card, "suit", "") or "").lower()
        if enhancement == "wild":
            effective = ("red", "black") if smeared else ("hearts", "diamonds", "spades", "clubs")
        elif smeared and suit in {"hearts", "diamonds"}:
            effective = ("red",)
        elif smeared and suit in {"spades", "clubs"}:
            effective = ("black",)
        else:
            effective = (suit,) if suit else ()
        for key in effective:
            suits[key] = suits.get(key, 0) + 1
    return _band(max(suits.values(), default=0), ((16, 1.0), (20, 3.0), (24, 5.0), (30, 7.0)))


def evaluate_flush_bond(state: Any) -> BondDevelopment:
    dev = _hand_bond(state, "flush", "FLUSH", (
        (FLUSH_XMULT, 6.0, "Flush XMult payoff"),
        (FLUSH_MULT, 4.0, "Flush Mult payoff"),
        (FLUSH_CHIPS, 4.0, "Flush Chips payoff"),
        (SUIT_MERGE_RED_BLACK, 5.0, "Suit merge"),
        (FOUR_CARD_STRAIGHT_FLUSH, 3.0, "Four-card flush support"),
    ))
    parts = list(dev.contributions)
    density = _flush_density(state)
    if density:
        parts.append(state_contribution(
            "deck:dominant_suit_density",
            "Dominant suit density",
            density,
            mechanic="dominant_suit_density",
        ))
    return finalize_development("flush", parts, HAND_THRESHOLDS, target="FLUSH")


def evaluate_full_house_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "full_house", "FULL_HOUSE", (
        (CONTAINS_PAIR_XMULT, 2.0, "Pair component"),
        (CONTAINS_THREE_XMULT, 2.0, "Three-kind component"),
    ), FULL_HOUSE_THRESHOLDS)


def evaluate_straight_flush_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "straight_flush", "STRAIGHT_FLUSH", (
        (FOUR_CARD_STRAIGHT_FLUSH, 4.0, "Four-card straight-flush support"),
        (STRAIGHT_GAP_RELAXATION, 3.0, "Straight gap relaxation"),
        (SUIT_MERGE_RED_BLACK, 3.0, "Suit merge"),
    ))


def evaluate_five_kind_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        _append_mechanic(parts, joker, index, DUPLICATE_SELECTED_CARD, 4.0, "Card duplication")
    ranks: dict[str, int] = {}
    for card in _deck(state):
        if str(getattr(card, "enhancement", "") or "").lower() == "stone":
            continue
        rank = str(getattr(card, "rank", "") or "")
        if rank:
            ranks[rank] = ranks.get(rank, 0) + 1
    concentration = _band(max(ranks.values(), default=0), ((5, 2.0), (7, 4.0), (10, 6.0), (14, 8.0)))
    if concentration:
        parts.append(state_contribution(
            "deck:max_rank_concentration",
            "Maximum rank concentration",
            concentration,
            mechanic="rank_concentration",
        ))
    level = _level_score(_hand_level(state, "FIVE_OF_A_KIND"))
    if level:
        parts.append(state_contribution(
            "hand_level:FIVE_OF_A_KIND",
            "FIVE_OF_A_KIND permanent hand level",
            level,
            mechanic="permanent_hand_level",
        ))
    return finalize_development("five_kind", parts, HAND_THRESHOLDS, target="FIVE_OF_A_KIND")


def evaluate_flush_house_bond(state: Any) -> BondDevelopment:
    return _hand_bond(state, "flush_house", "FLUSH_HOUSE", (
        (SUIT_MERGE_RED_BLACK, 3.0, "Suit merge"),
        (CONTAINS_PAIR_XMULT, 1.0, "Pair component"),
        (CONTAINS_THREE_XMULT, 1.0, "Three-kind component"),
    ), FLUSH_HOUSE_THRESHOLDS)


def evaluate_flush_five_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        _append_mechanic(parts, joker, index, DUPLICATE_SELECTED_CARD, 3.0, "Card duplication")
        _append_mechanic(parts, joker, index, SUIT_MERGE_RED_BLACK, 2.0, "Suit merge")
    groups: dict[tuple[str, str], int] = {}
    for card in _deck(state):
        if str(getattr(card, "enhancement", "") or "").lower() == "stone":
            continue
        key = (str(getattr(card, "rank", "") or ""), str(getattr(card, "suit", "") or ""))
        if all(key):
            groups[key] = groups.get(key, 0) + 1
    concentration = _band(max(groups.values(), default=0), ((5, 3.0), (7, 5.0), (10, 7.0)))
    if concentration:
        parts.append(state_contribution(
            "deck:same_rank_same_suit_concentration",
            "Same-rank same-suit concentration",
            concentration,
            mechanic="same_rank_same_suit_concentration",
        ))
    level = _level_score(_hand_level(state, "FLUSH_FIVE"))
    if level:
        parts.append(state_contribution(
            "hand_level:FLUSH_FIVE",
            "FLUSH_FIVE permanent hand level",
            level,
            mechanic="permanent_hand_level",
        ))
    return finalize_development("flush_five", parts, HAND_THRESHOLDS, target="FLUSH_FIVE")


def evaluate_played_retrigger_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    weights = (
        (RETRIGGER_PLAYED_FACE, 6.0, "Face-card retrigger"),
        (RETRIGGER_PLAYED_LOW_RANK, 6.0, "Low-rank retrigger"),
        (RETRIGGER_FIRST_SCORED, 6.0, "First-scored retrigger"),
        (RETRIGGER_FINAL_HAND, 4.0, "Final-hand retrigger"),
    )
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        for mechanic, value, label in weights:
            _append_mechanic(parts, joker, index, mechanic, value, label)
    red = sum(1 for card in _deck(state) if str(getattr(card, "seal", "") or "").lower() == "red")
    score = _band(red, ((1, 1.0), (2, 3.0), (4, 5.0), (7, 7.0)))
    if score:
        parts.append(state_contribution(
            "deck:red_seal_density",
            "Red Seal played-card infrastructure",
            score,
            mechanic="red_seal_density",
        ))
    return finalize_development("played_retrigger", parts, PLAYED_RETRIGGER_THRESHOLDS)


def evaluate_deck_growth_bond(state: Any) -> BondDevelopment:
    parts: list[BondContribution] = []
    weights = (
        (ADD_SEALED_CARD, 5.0, "Sealed-card generation"),
        (DUPLICATE_SELECTED_CARD, 6.0, "Card duplication"),
        (ADD_STONE_CARD, 3.0, "Stone-card generation"),
        (SCALE_ON_CARD_ADDED, 4.0, "Added-card scaling"),
    )
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        for mechanic, value, label in weights:
            _append_mechanic(parts, joker, index, mechanic, value, label)
    starting = starting_deck_size_for_name(getattr(state, "deck_name", None)) or 52
    growth = max(0, len(_deck(state)) - int(starting))
    score = _band(growth, ((4, 1.0), (8, 3.0), (12, 5.0), (18, 7.0)))
    if score:
        parts.append(state_contribution(
            "deck:permanent_growth",
            "Permanent deck growth",
            score,
            mechanic="permanent_deck_growth",
        ))
    return finalize_development("deck_growth", parts, DECK_GROWTH_THRESHOLDS)


MECHANICAL_PATTERN_EVALUATORS = {
    "pair": evaluate_pair_bond,
    "high_card": evaluate_high_card_bond,
    "two_pair": evaluate_two_pair_bond,
    "three_kind": evaluate_three_kind_bond,
    "four_kind": evaluate_four_kind_bond,
    "straight": evaluate_straight_bond,
    "flush": evaluate_flush_bond,
    "full_house": evaluate_full_house_bond,
    "straight_flush": evaluate_straight_flush_bond,
    "five_kind": evaluate_five_kind_bond,
    "flush_house": evaluate_flush_house_bond,
    "flush_five": evaluate_flush_five_bond,
    "played_retrigger": evaluate_played_retrigger_bond,
    "deck_growth": evaluate_deck_growth_bond,
}
