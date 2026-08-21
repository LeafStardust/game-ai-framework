from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
)


HELD_CARDS_BOND_ID = "held_cards"

# Provisional Red/White calibration. Held Cards has no defining unlock Joker;
# it emerges gradually from genuine held-card payoff infrastructure.
HELD_CARDS_RANK_THRESHOLDS: dict[BondRank, float] = {
    BondRank.R1: 4.0,
    BondRank.R2: 8.0,
    BondRank.R3: 13.0,
    BondRank.R4: 19.0,
    BondRank.R5: 26.0,
}

HELD_CARDS_RANK_POLICIES: dict[BondRank, tuple[str, ...]] = {
    BondRank.R1: (
        "recognize_held_card_payoff",
        "avoid_needlessly_spending_useful_held_payoff_cards",
    ),
    BondRank.R2: (
        "prefer_held_card_infrastructure_when_build_compatible",
        "preserve_useful_held_cards_more_consistently",
    ),
    BondRank.R3: (
        "actively_shape_hand_and_deck_toward_held_payoff",
        "protect_material_held_card_contributors",
        "increase_value_of_held_retrigger_and_steel_synergy",
    ),
    BondRank.R4: (
        "eligible_as_power_engine",
        "strongly_prioritize_hand_size_and_held_payoff_efficiency",
        "actively_seek_compatible_held_card_motifs",
    ),
    BondRank.R5: (
        "capstone_held_card_commitment",
        "aggressively_optimize_compatible_build_around_held_value",
        "abandon_only_for_survival_or_clearly_superior_composition",
    ),
}


def _name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains_named(values: Iterable[Any], *tokens: str) -> bool:
    normalized = {_name(value) for value in values}
    return any(
        any(token in candidate for candidate in normalized)
        for token in tokens
    )


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(count: int, bands: tuple[tuple[int, float], ...]) -> float:
    value = 0.0
    for threshold, score in bands:
        if count >= threshold:
            value = score
        else:
            break
    return value


def _steel_contribution(state: Any) -> float:
    count = sum(
        1
        for card in _owned_deck(state)
        if str(getattr(card, "enhancement", "") or "").strip().lower() == "steel"
    )
    return _band(count, ((1, 1.0), (2, 3.0), (4, 5.0), (6, 7.0)))


def _hand_size_contribution(state: Any) -> float:
    size = int(getattr(state, "hand_size", 8) or 8)
    return float(min(3, max(0, size - 8)))


def _has_direct_held_payoff(jokers: list[Any], steel: float) -> bool:
    return (
        _contains_named(jokers, "baronjoker", "baron")
        or _contains_named(jokers, "shootthemoonjoker", "shootthemoon")
        or _contains_named(jokers, "raisedfistjoker", "raisedfist")
        or steel > 0.0
    )


def _rank_for(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (
        BondRank.R1,
        BondRank.R2,
        BondRank.R3,
        BondRank.R4,
        BondRank.R5,
    ):
        if total >= HELD_CARDS_RANK_THRESHOLDS[candidate]:
            rank = candidate
        else:
            return rank, HELD_CARDS_RANK_THRESHOLDS[candidate]
    return BondRank.R5, None


def evaluate_held_cards_bond(state: Any) -> BondDevelopment:
    """Evaluate structural Held Cards Bond development.

    Held Cards has no hard unlock prerequisite. Only mechanics whose strategic
    payoff genuinely depends on cards remaining in hand contribute directly.

    Baron, Shoot the Moon and Raised Fist are direct held-card payoff Jokers.
    Steel density contributes because Steel itself scores while held. Extra hand
    size supports the axis modestly. Mime is a conditional bridge: it contributes
    here only when a genuine held-card payoff already exists, while its primary
    identity remains the separate Held Retrigger Bond.

    Gold cards and Blue Seals are intentionally excluded. Although they trigger
    while held, their strategic purpose is economy/Planet generation rather than
    development of the Held Cards power axis.
    """

    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    if _contains_named(jokers, "baronjoker", "baron"):
        parts.append(BondContribution("Baron", 6.0))
    if _contains_named(jokers, "shootthemoonjoker", "shootthemoon"):
        parts.append(BondContribution("Shoot the Moon", 4.0))
    if _contains_named(jokers, "raisedfistjoker", "raisedfist"):
        parts.append(BondContribution("Raised Fist", 2.0))

    steel = _steel_contribution(state)
    if steel > 0.0:
        parts.append(BondContribution("Steel held-card infrastructure", steel))

    if (
        _contains_named(jokers, "mimejoker", "mime")
        and _has_direct_held_payoff(jokers, steel)
    ):
        parts.append(BondContribution("Mime bridge", 2.0))

    hand_size = _hand_size_contribution(state)
    if hand_size > 0.0:
        parts.append(BondContribution("Extra hand size", hand_size))

    total = sum(part.value for part in parts)
    rank, next_threshold = _rank_for(total)

    return BondDevelopment(
        bond_id=HELD_CARDS_BOND_ID,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        realization=(
            BondRealization.DORMANT
            if rank == BondRank.R0
            else BondRealization.PARTIAL
        ),
    )
