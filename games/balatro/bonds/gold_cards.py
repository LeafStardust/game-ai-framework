from __future__ import annotations

from typing import Any

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    GOLD_CARD_GENERATION,
    GOLD_CARD_SCORING_ECONOMY,
    HELD_FACE_ECONOMY,
    components_have_mechanic,
)

GOLD_CARDS_BOND_ID = "gold_cards"
# The complete structural package tops out at 21 contribution:
# scoring Gold payoff (5) + Gold generator (5) + held-face economy (2)
# + dense Gold deck (9).
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


def _rank(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = GOLD_CARDS_THRESHOLDS[candidate]
        if total < threshold:
            return rank, threshold
        rank = candidate
    return BondRank.R5, None


def evaluate_gold_cards_bond(state: Any) -> BondDevelopment:
    """Evaluate persistent Gold-card infrastructure from public mechanics."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    if components_have_mechanic(jokers, GOLD_CARD_SCORING_ECONOMY):
        parts.append(BondContribution("Gold-card scoring economy", 5.0))
    if components_have_mechanic(jokers, GOLD_CARD_GENERATION):
        parts.append(BondContribution("Gold-card generation", 5.0))
    if components_have_mechanic(jokers, HELD_FACE_ECONOMY):
        parts.append(BondContribution("Held-face economy", 2.0))

    gold_count = sum(
        1
        for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").lower() == "gold"
    )
    density = _band(gold_count, ((1, 1.0), (3, 3.0), (6, 6.0), (10, 9.0)))
    if density:
        parts.append(BondContribution("Gold card density", density))

    total = sum(part.value for part in parts)
    rank, next_threshold = _rank(total)
    return BondDevelopment(
        bond_id=GOLD_CARDS_BOND_ID,
        unlocked=total > 0.0,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )
