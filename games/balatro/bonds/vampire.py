from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization

VAMPIRE_BOND_ID = "vampire"
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
    frozenset(("vampire", "enhanced_cards")): "CONFLICT",
}


def _name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


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


def _locked() -> BondDevelopment:
    return BondDevelopment(
        bond_id=VAMPIRE_BOND_ID,
        unlocked=False,
        contribution=0.0,
        rank=BondRank.LOCKED,
        next_rank_threshold=VAMPIRE_THRESHOLDS[BondRank.R1],
        contributions=(),
        realization=BondRealization.DORMANT,
    )


def evaluate_vampire_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "vampire"):
        return _locked()

    parts = [BondContribution("Vampire", 7.0)]

    if _contains(jokers, "midasmask"):
        parts.append(BondContribution("Midas Mask renewable feed bridge", 5.0))
    if _contains(jokers, "cartomancer"):
        parts.append(BondContribution("Cartomancer enhancement-feed access", 2.0))

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
        parts.append(BondContribution("Vampire accumulated consumption", history))

    total = sum(part.value for part in parts)
    rank, nxt = _rank(total)
    return BondDevelopment(
        bond_id=VAMPIRE_BOND_ID,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=nxt,
        contributions=tuple(parts),
        realization=BondRealization.PARTIAL,
    )
