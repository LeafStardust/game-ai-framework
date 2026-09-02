from __future__ import annotations

"""Descriptor-driven evaluators for the final legacy catalogue residue."""

from typing import Any

from games.balatro.bonds import catalogue_batch_one as b1
from games.balatro.bonds import catalogue_batch_two as b2
from games.balatro.bonds import catalogue_batch_three as b3
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    ACE_CHIPS_MULT,
    ADD_STONE_CARD,
    ALL_CARDS_FACE,
    CASH_CHIPS,
    CASH_MULT,
    DISCARDS_TO_HANDS,
    DUPLICATE_SELECTED_CARD,
    FACE_CASH,
    FACE_CHIPS,
    FACE_MULT,
    FACE_XMULT_FIRST,
    GLASS_PAYOFF,
    HELD_FACE_ECONOMY,
    INTEREST_AMPLIFICATION,
    LOW_RANK_EVEN_MULT,
    LOW_RANK_FIBONACCI_MULT,
    LOW_RANK_FOUR_TEN,
    LOW_RANK_RETRIGGER,
    LOW_RANK_TWO_SCALING,
    LUCKY_TRIGGER_SCALING,
    NO_DISCARD_ECONOMY,
    NO_DISCARD_SCALING,
    NO_DISCARD_XMULT,
    PASSIVE_CASH,
    PROBABILITY_DOUBLING,
    RANK_NINE_CASH,
    RETRIGGER_PLAYED_FACE,
    ROUND_CASH_GROWTH,
    STONE_PAYOFF,
    SUIT_CLUBS_MULT_MAJOR,
    SUIT_CLUBS_MULT_MINOR,
    SUIT_DIAMONDS_CASH,
    SUIT_DIAMONDS_MULT,
    SUIT_HEARTS_MULT,
    SUIT_HEARTS_XMULT,
    SUIT_SPADES_CHIPS,
    SUIT_SPADES_MULT,
    UNIQUE_PLANET_CASH,
    UNUSED_DISCARD_CHIPS,
    component_has_mechanic,
)


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


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = thresholds[candidate]
        if total < threshold:
            return rank, threshold
        rank = candidate
    return BondRank.R5, None


def _finish(
    bond_id: str,
    parts: list[BondContribution],
    thresholds: dict[BondRank, float],
    *,
    target: str | None = None,
) -> BondDevelopment:
    total = sum(part.value for part in parts)
    rank, next_threshold = _rank(total, thresholds)
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target=target,
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return fallback if cls in {"str", "SimpleNamespace"} else cls


def _mechanic_parts(
    state: Any,
    weights: tuple[tuple[str, float, str], ...],
) -> list[BondContribution]:
    parts: list[BondContribution] = []
    for joker in list(getattr(state, "jokers", ()) or ()):
        for mechanic, value, label in weights:
            if component_has_mechanic(joker, mechanic):
                parts.append(BondContribution(_source(joker, label), value))
    return parts


def evaluate_aces_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (ACE_CHIPS_MULT, 6.0, "Ace chips/Mult payoff"),
        (LOW_RANK_FIBONACCI_MULT, 3.0, "Ace Fibonacci payoff"),
    ))
    aces = sum(1 for card in _deck(state) if str(getattr(card, "rank", "") or "").upper() == "A")
    score = _band(aces, ((4, 1.0), (6, 3.0), (8, 5.0), (12, 7.0)))
    if score:
        parts.append(BondContribution("Ace density", score))
    if aces >= 6:
        for joker in list(getattr(state, "jokers", ()) or ()):
            if component_has_mechanic(joker, DUPLICATE_SELECTED_CARD):
                parts.append(BondContribution(_source(joker, "Ace duplication bridge"), 4.0))
                break
    return _finish("aces", parts, b1.ACES_THRESHOLDS, target="A")


def evaluate_no_discard_bond(state: Any) -> BondDevelopment:
    return _finish("no_discard", _mechanic_parts(state, (
        (NO_DISCARD_SCALING, 6.0, "No-discard scaling"),
        (DISCARDS_TO_HANDS, 6.0, "Discard-to-hand conversion"),
        (NO_DISCARD_ECONOMY, 4.0, "Unused-discard economy"),
        (NO_DISCARD_XMULT, 4.0, "No-discard XMult"),
        (UNUSED_DISCARD_CHIPS, 2.0, "Unused-discard chips"),
    )), b1.NO_DISCARD_THRESHOLDS)


def evaluate_cash_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (CASH_CHIPS, 5.0, "Cash-to-chips payoff"),
        (CASH_MULT, 5.0, "Cash-to-Mult payoff"),
        (ROUND_CASH_GROWTH, 4.0, "Round cash growth"),
        (PASSIVE_CASH, 3.0, "Passive cash"),
        (INTEREST_AMPLIFICATION, 3.0, "Interest amplification"),
        (UNIQUE_PLANET_CASH, 3.0, "Planet diversity cash"),
        (HELD_FACE_ECONOMY, 2.0, "Held-face economy"),
        (RANK_NINE_CASH, 3.0, "Nine-card economy"),
    ))
    money = int(getattr(state, "money", 0) or 0)
    score = _band(money, ((25, 1.0), (50, 3.0), (100, 5.0), (150, 7.0)))
    if score:
        parts.append(BondContribution("Current bankroll", score))
    return _finish("cash", parts, b1.CASH_THRESHOLDS)


def evaluate_lucky_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (LUCKY_TRIGGER_SCALING, 6.0, "Lucky trigger scaling"),
        (PROBABILITY_DOUBLING, 4.0, "Probability amplification"),
    ))
    count = sum(1 for card in _deck(state) if str(getattr(card, "enhancement", "") or "").lower() == "lucky")
    score = _band(count, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if score:
        parts.append(BondContribution("Lucky card density", score))
    return _finish("lucky", parts, b1.LUCKY_THRESHOLDS)


def evaluate_glass_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, ((GLASS_PAYOFF, 6.0, "Glass destruction payoff"),))
    count = sum(1 for card in _deck(state) if str(getattr(card, "enhancement", "") or "").lower() == "glass")
    score = _band(count, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if score:
        parts.append(BondContribution("Glass card density", score))
    has_payoff = any(component_has_mechanic(j, GLASS_PAYOFF) for j in list(getattr(state, "jokers", ()) or ()))
    destroyed = int(getattr(state, "glass_cards_destroyed", 0) or 0)
    history = _band(destroyed, ((1, 1.0), (3, 2.0), (6, 4.0), (10, 6.0))) if has_payoff else 0.0
    if history:
        parts.append(BondContribution("Accumulated Glass destruction", history))
    return _finish("glass", parts, b1.GLASS_THRESHOLDS)


def evaluate_face_cards_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (ALL_CARDS_FACE, 6.0, "All-cards-face enabling"),
        (RETRIGGER_PLAYED_FACE, 5.0, "Face-card retrigger"),
        (FACE_XMULT_FIRST, 4.0, "First-face XMult"),
        (FACE_CHIPS, 4.0, "Face-card chips"),
        (FACE_MULT, 4.0, "Face-card Mult"),
        (FACE_CASH, 2.0, "Face-card economy"),
    ))
    count = sum(1 for card in _deck(state) if str(getattr(card, "rank", "") or "").upper() in {"J", "Q", "K"})
    score = _band(count, ((12, 1.0), (16, 3.0), (20, 5.0), (26, 7.0)))
    if score:
        parts.append(BondContribution("Face-card density", score))
    return _finish("face_cards", parts, b1.FACE_CARDS_THRESHOLDS, target="J/Q/K")


def evaluate_stone_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (STONE_PAYOFF, 6.0, "Stone-card payoff"),
        (ADD_STONE_CARD, 5.0, "Stone-card generation"),
    ))
    count = sum(1 for card in _deck(state) if str(getattr(card, "enhancement", "") or "").lower() == "stone")
    score = _band(count, ((1, 1.0), (3, 3.0), (6, 6.0), (10, 9.0)))
    if score:
        parts.append(BondContribution("Stone card density", score))
    return _finish("stone", parts, b2.STONE_THRESHOLDS)


def _suit_bond(
    state: Any,
    bond_id: str,
    suit: str,
    weights: tuple[tuple[str, float, str], ...],
    thresholds: dict[BondRank, float],
) -> BondDevelopment:
    parts = _mechanic_parts(state, weights)
    count = sum(
        1
        for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").lower() != "stone"
        and (
            str(getattr(card, "suit", "") or "").lower() == suit.lower()
            or str(getattr(card, "enhancement", "") or "").lower() == "wild"
        )
    )
    score = _band(count, ((13, 1.0), (17, 3.0), (21, 5.0), (26, 7.0), (32, 9.0)))
    if score:
        parts.append(BondContribution(f"{suit} density", score))
    return _finish(bond_id, parts, thresholds, target=suit.upper())


def evaluate_hearts_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "hearts", "Hearts", (
        (SUIT_HEARTS_XMULT, 7.0, "Hearts XMult payoff"),
        (SUIT_HEARTS_MULT, 4.0, "Hearts Mult payoff"),
    ), b3.HEARTS_THRESHOLDS)


def evaluate_spades_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "spades", "Spades", (
        (SUIT_SPADES_CHIPS, 6.0, "Spades chips payoff"),
        (SUIT_SPADES_MULT, 4.0, "Spades Mult payoff"),
    ), b3.SPADES_THRESHOLDS)


def evaluate_clubs_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "clubs", "Clubs", (
        (SUIT_CLUBS_MULT_MAJOR, 6.0, "Clubs major Mult payoff"),
        (SUIT_CLUBS_MULT_MINOR, 4.0, "Clubs minor Mult payoff"),
    ), b3.CLUBS_THRESHOLDS)


def evaluate_diamonds_bond(state: Any) -> BondDevelopment:
    return _suit_bond(state, "diamonds", "Diamonds", (
        (SUIT_DIAMONDS_CASH, 6.0, "Diamonds economy payoff"),
        (SUIT_DIAMONDS_MULT, 4.0, "Diamonds Mult payoff"),
    ), b3.DIAMONDS_THRESHOLDS)


def evaluate_low_ranks_bond(state: Any) -> BondDevelopment:
    parts = _mechanic_parts(state, (
        (LOW_RANK_RETRIGGER, 6.0, "Low-rank retrigger"),
        (LOW_RANK_TWO_SCALING, 5.0, "Two-rank scaling"),
        (LOW_RANK_FIBONACCI_MULT, 4.0, "Low-rank Fibonacci payoff"),
        (LOW_RANK_EVEN_MULT, 3.0, "Even-rank Mult"),
        (LOW_RANK_FOUR_TEN, 2.0, "Four/Ten payoff"),
    ))
    count = sum(1 for card in _deck(state) if str(getattr(card, "rank", "") or "") in {"2", "3", "4", "5"})
    score = _band(count, ((16, 1.0), (20, 3.0), (24, 5.0), (30, 7.0)))
    if score:
        parts.append(BondContribution("2-5 density", score))
    return _finish("low_ranks", parts, b3.LOW_RANKS_THRESHOLDS, target="2-5")


MECHANICAL_RESIDUE_EVALUATORS = {
    "aces": evaluate_aces_bond,
    "no_discard": evaluate_no_discard_bond,
    "cash": evaluate_cash_bond,
    "lucky": evaluate_lucky_bond,
    "glass": evaluate_glass_bond,
    "face_cards": evaluate_face_cards_bond,
    "stone": evaluate_stone_bond,
    "hearts": evaluate_hearts_bond,
    "spades": evaluate_spades_bond,
    "clubs": evaluate_clubs_bond,
    "diamonds": evaluate_diamonds_bond,
    "low_ranks": evaluate_low_ranks_bond,
}
