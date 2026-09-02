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
    CARD_DESTRUCTION,
    DECK_THIN_PAYOFF,
    HAND_LEVEL_COPY,
    RETRIGGER_HELD_CARDS,
    SPECTRAL_GENERATION,
    STEEL_CARD_PAYOFF,
    component_has_mechanic,
)


# Post-audit reachable capstones retained from the validated Phase B geometry.
HELD_RETRIGGER_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 17.0,
    BondRank.R5: 21.0,
}
STEEL_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 17.0,
    BondRank.R5: 20.0,
}
DECK_THINNING_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 7.0,
    BondRank.R3: 10.0,
    BondRank.R4: 13.0,
    BondRank.R5: 16.0,
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


def _source_label(component: Any, fallback: str) -> str:
    raw = getattr(component, "name", None)
    if raw:
        return str(raw)
    class_name = component.__class__.__name__
    return class_name if class_name not in {"str", "SimpleNamespace"} else fallback


def evaluate_held_retrigger_bond(state: Any) -> BondDevelopment:
    """Evaluate held-card retrigger infrastructure through the Phase C ledger."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []
    retrigger_indexes: list[int] = []

    for index, component in enumerate(jokers):
        if component_has_mechanic(component, RETRIGGER_HELD_CARDS):
            retrigger_indexes.append(index)
            parts.append(component_contribution(
                component,
                collection="jokers",
                index=index,
                label=_source_label(component, "Held retrigger source"),
                value=6.0,
                mechanic=RETRIGGER_HELD_CARDS,
            ))

    red = sum(
        1 for card in _owned_deck(state)
        if str(getattr(card, "seal", "") or "").strip().lower() == "red"
    )
    red_score = _band(red, ((1, 1.0), (2, 3.0), (4, 5.0), (6, 7.0)))
    if red_score:
        parts.append(state_contribution(
            "deck:red_seal_density",
            "Red Seal retrigger infrastructure",
            red_score,
            mechanic="red_seal_density",
        ))

    if retrigger_indexes:
        for index, copier in enumerate(jokers):
            if component_has_mechanic(copier, HAND_LEVEL_COPY):
                parts.append(component_contribution(
                    copier,
                    collection="jokers",
                    index=index,
                    label=_source_label(copier, "Copy engine"),
                    value=4.0,
                    mechanic=HAND_LEVEL_COPY,
                ))

    return finalize_development("held_retrigger", parts, HELD_RETRIGGER_THRESHOLDS)


def evaluate_steel_bond(state: Any) -> BondDevelopment:
    """Evaluate Steel infrastructure through the Phase C ledger."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    for index, component in enumerate(jokers):
        if component_has_mechanic(component, STEEL_CARD_PAYOFF):
            parts.append(component_contribution(
                component,
                collection="jokers",
                index=index,
                label=_source_label(component, "Steel payoff"),
                value=5.0,
                mechanic=STEEL_CARD_PAYOFF,
            ))

    steel_cards = [
        card for card in _owned_deck(state)
        if str(getattr(card, "enhancement", "") or "").strip().lower() == "steel"
    ]
    density = _band(len(steel_cards), ((1, 1.0), (2, 3.0), (4, 6.0), (6, 9.0), (10, 12.0)))
    if density:
        parts.append(state_contribution(
            "deck:steel_density",
            "Steel card density",
            density,
            mechanic="steel_card_density",
        ))

    red_steel = sum(
        1 for card in steel_cards
        if str(getattr(card, "seal", "") or "").strip().lower() == "red"
    )
    overlap = _band(red_steel, ((1, 1.0), (2, 2.0), (4, 3.0)))
    if overlap:
        parts.append(state_contribution(
            "deck:red_steel_density",
            "Red-Seal Steel overlap",
            overlap,
            mechanic="red_seal_steel_density",
        ))

    return finalize_development("steel", parts, STEEL_THRESHOLDS)


def evaluate_deck_thinning_bond(state: Any) -> BondDevelopment:
    """Evaluate removal infrastructure with same-source deduplication."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    for index, component in enumerate(jokers):
        if component_has_mechanic(component, DECK_THIN_PAYOFF):
            parts.append(component_contribution(
                component,
                collection="jokers",
                index=index,
                label=_source_label(component, "Deck-thin payoff"),
                value=7.0,
                mechanic=DECK_THIN_PAYOFF,
            ))
        if component_has_mechanic(component, CARD_DESTRUCTION):
            value = 4.0 if component_has_mechanic(component, SPECTRAL_GENERATION) else 5.0
            parts.append(component_contribution(
                component,
                collection="jokers",
                index=index,
                label=_source_label(component, "Card-destruction engine"),
                value=value,
                mechanic=CARD_DESTRUCTION,
            ))

    starting_size = starting_deck_size_for_name(getattr(state, "deck_name", None)) or 52
    reduction = max(0, int(starting_size) - len(_owned_deck(state)))
    score = _band(reduction, ((4, 1.0), (8, 3.0), (12, 5.0), (18, 7.0)))
    if score:
        parts.append(state_contribution(
            "deck:permanent_reduction",
            "Permanent deck reduction",
            score,
            mechanic="permanent_deck_reduction",
        ))

    return finalize_development("deck_thinning", parts, DECK_THINNING_THRESHOLDS)
