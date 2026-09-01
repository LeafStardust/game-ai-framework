from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization

GOLD_CARDS_BOND_ID = "gold_cards"
GOLD_CARDS_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(value) for value in values}
    return any(any(token in name for name in names) for token in tokens)


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
    """Evaluate persistent Gold-card infrastructure, separate from generic cash."""
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    if _contains(jokers, "goldenticket"):
        parts.append(BondContribution("Golden Ticket", 5.0))
    if _contains(jokers, "midasmask"):
        parts.append(BondContribution("Midas Mask", 5.0))
    if _contains(jokers, "reservedparking"):
        parts.append(BondContribution("Reserved Parking held-card economy", 2.0))

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
