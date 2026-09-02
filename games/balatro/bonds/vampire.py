from __future__ import annotations

from typing import Any

from games.balatro.bonds.contributions import component_contribution, finalize_development, state_contribution
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.mechanics import (
    ENHANCEMENT_CONSUMPTION,
    ENHANCEMENT_FEED_ACCESS,
    TAROT_GENERATION,
    component_has_mechanic,
)

ENHANCEMENT_CONSUMPTION_BOND_ID = "enhancement_consumption"
VAMPIRE_BOND_ID = ENHANCEMENT_CONSUMPTION_BOND_ID
VAMPIRE_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 17.0,
    BondRank.R5: 21.0,
}
VAMPIRE_POLICIES = {
    BondRank.R1: ("recognize_vampire_enhancement_consumption",),
    BondRank.R2: ("prefer_safe_enhancement_feed_lines",),
    BondRank.R3: ("actively_generate_feedstock_for_vampire",),
    BondRank.R4: ("eligible_as_power_engine",),
    BondRank.R5: ("capstone_vampire_feed_engine",),
}
VAMPIRE_RELATIONSHIPS = {
    frozenset((ENHANCEMENT_CONSUMPTION_BOND_ID, "enhanced_cards")): "CONFLICT",
}


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    out = 0.0
    for threshold, score in bands:
        if value >= threshold:
            out = score
        else:
            break
    return out


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return fallback if cls in {"str", "SimpleNamespace"} else cls


def evaluate_enhancement_consumption_bond(state: Any) -> BondDevelopment:
    """Evaluate enhancement-feed/consumption infrastructure through the ledger."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []
    has_consumer = any(component_has_mechanic(j, ENHANCEMENT_CONSUMPTION) for j in jokers)

    for index, joker in enumerate(jokers):
        if component_has_mechanic(joker, ENHANCEMENT_CONSUMPTION):
            mechanic, value, label = ENHANCEMENT_CONSUMPTION, 7.0, "Enhancement consumer"
        elif component_has_mechanic(joker, ENHANCEMENT_FEED_ACCESS):
            mechanic, value, label = ENHANCEMENT_FEED_ACCESS, (5.0 if has_consumer else 2.0), "Renewable enhancement feed bridge"
        elif component_has_mechanic(joker, TAROT_GENERATION):
            mechanic, value, label = TAROT_GENERATION, (2.0 if has_consumer else 1.0), "Consumable enhancement-feed access"
        else:
            continue
        parts.append(component_contribution(
            joker,
            collection="jokers",
            index=index,
            label=_source(joker, label),
            value=value,
            mechanic=mechanic,
        ))

    enhanced = sum(
        1 for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").strip()
    )
    density = _band(enhanced, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if density:
        parts.append(state_contribution(
            "deck:enhancement_feedstock",
            "Current enhancement feedstock",
            density,
            mechanic="enhancement_feedstock_density",
        ))

    consumed = int(getattr(state, "vampire_enhancements_consumed", 0) or 0)
    history = _band(consumed, ((3, 1.0), (8, 2.0), (15, 4.0), (25, 6.0)))
    if history:
        parts.append(state_contribution(
            "history:enhancements_consumed",
            "Accumulated enhancement consumption",
            history,
            mechanic="enhancement_consumption_history",
        ))

    return finalize_development(
        ENHANCEMENT_CONSUMPTION_BOND_ID,
        parts,
        VAMPIRE_THRESHOLDS,
        unlocked=bool(parts),
    )


def evaluate_vampire_bond(state: Any) -> BondDevelopment:
    return evaluate_enhancement_consumption_bond(state)
