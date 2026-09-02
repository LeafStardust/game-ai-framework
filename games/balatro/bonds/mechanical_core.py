from __future__ import annotations

from typing import Any

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.mechanics import (
    CARD_DESTRUCTION,
    DECK_THIN_PAYOFF,
    HAND_LEVEL_COPY,
    RETRIGGER_HELD_CARDS,
    STEEL_CARD_PAYOFF,
    component_has_mechanic,
    components_have_mechanic,
    components_with_mechanic,
)


HELD_RETRIGGER_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}
STEEL_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 14.0,
    BondRank.R4: 21.0,
    BondRank.R5: 29.0,
}
DECK_THINNING_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    score = 0.0
    for threshold, candidate in bands:
        if value < threshold:
            break
        score = candidate
    return score


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
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _source_label(component: Any, fallback: str) -> str:
    raw = getattr(component, "name", None)
    if raw:
        return str(raw)
    class_name = component.__class__.__name__
    return class_name if class_name not in {"str", "SimpleNamespace"} else fallback


def evaluate_held_retrigger_bond(state: Any) -> BondDevelopment:
    """Evaluate held-card retrigger infrastructure from public mechanics."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    retriggers = components_with_mechanic(jokers, RETRIGGER_HELD_CARDS)
    for component in retriggers:
        parts.append(BondContribution(_source_label(component, "Held retrigger source"), 6.0))

    deck = _owned_deck(state)
    red = sum(
        1 for card in deck
        if str(getattr(card, "seal", "") or "").strip().lower() == "red"
    )
    red_score = _band(red, ((1, 1.0), (2, 3.0), (4, 5.0), (6, 7.0)))
    if red_score:
        parts.append(BondContribution("Red Seal retrigger infrastructure", red_score))

    if retriggers:
        for copier in components_with_mechanic(jokers, HAND_LEVEL_COPY):
            parts.append(BondContribution(_source_label(copier, "Copy engine"), 4.0))

    return _finish("held_retrigger", parts, HELD_RETRIGGER_THRESHOLDS)


def evaluate_steel_bond(state: Any) -> BondDevelopment:
    """Evaluate Steel infrastructure without identifying Steel Joker by name."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    for component in components_with_mechanic(jokers, STEEL_CARD_PAYOFF):
        parts.append(BondContribution(_source_label(component, "Steel payoff"), 5.0))

    steel_cards = [
        card for card in _owned_deck(state)
        if str(getattr(card, "enhancement", "") or "").strip().lower() == "steel"
    ]
    density = _band(len(steel_cards), ((1, 1.0), (2, 3.0), (4, 6.0), (6, 9.0), (10, 12.0)))
    if density:
        parts.append(BondContribution("Steel card density", density))

    red_steel = sum(
        1 for card in steel_cards
        if str(getattr(card, "seal", "") or "").strip().lower() == "red"
    )
    overlap = _band(red_steel, ((1, 1.0), (2, 2.0), (4, 3.0)))
    if overlap:
        parts.append(BondContribution("Red-Seal Steel overlap", overlap))

    return _finish("steel", parts, STEEL_THRESHOLDS)


def evaluate_deck_thinning_bond(state: Any) -> BondDevelopment:
    """Evaluate permanent removal infrastructure and reduced deck size."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    for component in jokers:
        if component_has_mechanic(component, DECK_THIN_PAYOFF):
            parts.append(BondContribution(_source_label(component, "Deck-thin payoff"), 7.0))
        if component_has_mechanic(component, CARD_DESTRUCTION):
            # Trading Card and Sixth Sense historically contribute different
            # amounts; use the explicit Spectral side effect to preserve the
            # latter's lower structural weighting without name checks.
            mechanics = getattr(component, "mechanics", ()) or ()
            value = 4.0 if "spectral_generation" in mechanics else 5.0
            parts.append(BondContribution(_source_label(component, "Card-destruction engine"), value))

    deck = _owned_deck(state)
    starting_size = starting_deck_size_for_name(getattr(state, "deck_name", None))
    if starting_size is None:
        starting_size = 52
    reduction = max(0, int(starting_size) - len(deck))
    score = _band(reduction, ((4, 1.0), (8, 3.0), (12, 5.0), (18, 7.0)))
    if score:
        parts.append(BondContribution("Permanent deck reduction", score))

    return _finish("deck_thinning", parts, DECK_THINNING_THRESHOLDS)
