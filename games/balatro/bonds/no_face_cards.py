from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization


NO_FACE_CARDS_BOND_ID = "no_face_cards"
NO_FACE_CARDS_RANK_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 10.0,
    BondRank.R4: 12.0,
    BondRank.R5: 14.0,
}
NO_FACE_CARDS_RANK_POLICIES = {
    BondRank.R1: ("recognize_ride_the_bus_no_face_payoff",),
    BondRank.R2: ("prefer_lines_that_do_not_score_face_cards",),
    BondRank.R3: ("actively_reduce_face_card_interference",),
    BondRank.R4: ("eligible_as_power_engine_when_bus_scaling_is_realized",),
    BondRank.R5: ("capstone_face_free_commitment",),
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


def _rank(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = NO_FACE_CARDS_RANK_THRESHOLDS[candidate]
        if total >= threshold:
            rank = candidate
        else:
            return rank, threshold
    return BondRank.R5, None


def _locked() -> BondDevelopment:
    return BondDevelopment(
        bond_id=NO_FACE_CARDS_BOND_ID,
        unlocked=False,
        contribution=0.0,
        rank=BondRank.LOCKED,
        next_rank_threshold=NO_FACE_CARDS_RANK_THRESHOLDS[BondRank.R1],
        contributions=(),
        realization=BondRealization.DORMANT,
    )


def evaluate_no_face_cards_bond(state: Any) -> BondDevelopment:
    """Evaluate Ride-the-Bus-defined no-face-card development.

    Natural J/Q/K depletion develops the Bond because it directly lowers the
    probability of accidentally resetting Ride the Bus when following the plan.
    Generic face-card interaction does not count as quota.
    """
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "ridethebusjoker", "ridethebus"):
        return _locked()

    parts = [BondContribution("Ride the Bus", 7.0)]
    deck = _deck(state)

    if deck:
        face_count = sum(
            1
            for card in deck
            if str(getattr(card, "rank", "") or "").upper() in {"J", "Q", "K"}
            and str(getattr(card, "enhancement", "") or "").lower() != "stone"
        )

        # Standard 52-card deck starts with 12 natural face cards. Lower density
        # is persistent structural commitment; zero natural faces is capstone support.
        density_score = 0.0
        if face_count == 0:
            density_score = 7.0
        elif face_count <= 3:
            density_score = 5.0
        elif face_count <= 6:
            density_score = 3.0
        elif face_count <= 9:
            density_score = 1.0

        if density_score:
            parts.append(BondContribution("Low natural face-card density", density_score))

    total = sum(part.value for part in parts)
    rank, next_threshold = _rank(total)
    return BondDevelopment(
        bond_id=NO_FACE_CARDS_BOND_ID,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target="NO_FACE_CARDS",
        realization=BondRealization.PARTIAL,
    )


NO_FACE_CARDS_RELATIONSHIPS = {
    frozenset(("face_cards", "no_face_cards")): "CONFLICT",
}
