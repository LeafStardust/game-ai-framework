from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import component_contribution, finalize_development, state_contribution
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.mechanics import (
    GOLD_CARD_GENERATION,
    GOLD_CARD_SCORING_ECONOMY,
    HELD_FACE_ECONOMY,
    component_has_mechanic,
)

GOLD_CARDS_BOND_ID = "gold_cards"
GOLD_CARDS_THRESHOLDS = {
    BondRank.R1: 3.0,
    BondRank.R2: 6.0,
    BondRank.R3: 10.0,
    BondRank.R4: 15.0,
    BondRank.R5: 21.0,
}


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    result = 0.0
    for threshold, score in bands:
        if value < threshold:
            break
        result = score
    return result


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return fallback if cls in {"str", "SimpleNamespace"} else cls


def evaluate_gold_cards_bond(state: Any) -> BondDevelopment:
    """Evaluate persistent Gold-card infrastructure through the canonical ledger."""
    parts: list[BondContribution] = []
    for index, joker in enumerate(list(getattr(state, "jokers", ()) or ())):
        for mechanic, value, label in (
            (GOLD_CARD_SCORING_ECONOMY, 5.0, "Gold-card scoring economy"),
            (GOLD_CARD_GENERATION, 5.0, "Gold-card generation"),
            (HELD_FACE_ECONOMY, 2.0, "Held-face economy"),
        ):
            if component_has_mechanic(joker, mechanic):
                parts.append(component_contribution(
                    joker,
                    collection="jokers",
                    index=index,
                    label=_source(joker, label),
                    value=value,
                    mechanic=mechanic,
                ))

    gold_count = sum(
        1
        for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").lower() == "gold"
    )
    density = _band(gold_count, ((1, 1.0), (3, 3.0), (6, 6.0), (10, 9.0)))
    if density:
        parts.append(state_contribution(
            "deck:gold_density",
            "Gold card density",
            density,
            mechanic="gold_card_density",
        ))

    return finalize_development(
        GOLD_CARDS_BOND_ID,
        parts,
        GOLD_CARDS_THRESHOLDS,
        unlocked=bool(parts),
    )
