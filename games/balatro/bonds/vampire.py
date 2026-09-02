from __future__ import annotations

from typing import Any

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    ENHANCEMENT_CONSUMPTION,
    ENHANCEMENT_FEED_ACCESS,
    TAROT_GENERATION,
    components_have_mechanic,
)

ENHANCEMENT_CONSUMPTION_BOND_ID = "enhancement_consumption"
# Temporary compatibility alias while callers/tests migrate.
VAMPIRE_BOND_ID = ENHANCEMENT_CONSUMPTION_BOND_ID
VAMPIRE_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 17.0,
    BondRank.R5: 21.0,
}
# Legacy diagnostic metadata only. It is not action authority in the new Bond model.
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


def _rank(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = VAMPIRE_THRESHOLDS[candidate]
        if total >= threshold:
            rank = candidate
        else:
            return rank, threshold
    return BondRank.R5, None


def evaluate_enhancement_consumption_bond(state: Any) -> BondDevelopment:
    """Evaluate enhancement-feed/consumption infrastructure from mechanics."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    has_consumer = components_have_mechanic(jokers, ENHANCEMENT_CONSUMPTION)
    if has_consumer:
        parts.append(BondContribution("Enhancement consumer", 7.0))
    if components_have_mechanic(jokers, ENHANCEMENT_FEED_ACCESS):
        parts.append(BondContribution("Renewable enhancement feed bridge", 5.0 if has_consumer else 2.0))
    if components_have_mechanic(jokers, TAROT_GENERATION):
        parts.append(BondContribution("Consumable enhancement-feed access", 2.0 if has_consumer else 1.0))

    enhanced = sum(
        1 for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").strip()
    )
    density = _band(enhanced, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if density:
        parts.append(BondContribution("Current enhancement feedstock", density))

    consumed = int(getattr(state, "vampire_enhancements_consumed", 0) or 0)
    history = _band(consumed, ((3, 1.0), (8, 2.0), (15, 4.0), (25, 6.0)))
    if history:
        parts.append(BondContribution("Accumulated enhancement consumption", history))

    total = sum(part.value for part in parts)
    rank, nxt = _rank(total)
    return BondDevelopment(
        bond_id=ENHANCEMENT_CONSUMPTION_BOND_ID,
        unlocked=total > 0.0,
        contribution=total,
        rank=rank,
        next_rank_threshold=nxt,
        contributions=tuple(parts),
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


# Temporary callable alias for production/tests that still import the legacy name.
def evaluate_vampire_bond(state: Any) -> BondDevelopment:
    return evaluate_enhancement_consumption_bond(state)
