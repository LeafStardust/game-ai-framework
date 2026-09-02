from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
)
from games.balatro.mechanics import (
    DISCARD_HAND_LEVELING,
    HAND_LEVEL_COPY,
    PLANET_PACK_TARGETING,
    PROBABILISTIC_HAND_LEVELING,
    components_have_mechanic,
    components_with_mechanic,
)


HAND_LEVELING_BOND_ID = "hand_leveling"
# Temporary compatibility name while callers/tests migrate. This is a Bond-ID
# alias only; Burnt Joker remains a legitimate mechanical component name.
BURNT_BOND_ID = HAND_LEVELING_BOND_ID
BURNT_SUPPORTED_TARGETS = frozenset({"HIGH_CARD", "PAIR"})

# Provisional weighted thresholds retained from the previous evaluator until the
# canonical BuildValue calibration phase. They are evidence bands, not authority.
BURNT_RANK_THRESHOLDS: dict[BondRank, float] = {
    BondRank.R1: 8.0,
    BondRank.R2: 12.0,
    BondRank.R3: 17.0,
    BondRank.R4: 23.0,
    BondRank.R5: 30.0,
}

# Legacy diagnostic policy metadata. Do not use this as action authority in the
# new architecture; it remains temporarily for compatibility during migration.
BURNT_RANK_POLICIES: dict[BondRank, tuple[str, ...]] = {
    BondRank.R1: (
        "recognize_first_discard_level_value",
        "default_target_high_card_without_stronger_hand_bond",
    ),
    BondRank.R2: (
        "reinforce_selected_target_hand",
        "prefer_targeted_hand_level_infrastructure",
        "preserve_reasonable_first_discard_access",
    ),
    BondRank.R3: (
        "actively_shape_resources_around_target_hand",
        "protect_material_burnt_contributors",
        "increase_search_value_for_burnt_reinforcement",
    ),
    BondRank.R4: (
        "eligible_as_power_engine",
        "activate_first_discard_before_trivial_clear_when_safe",
        "strongly_prioritize_targeted_permanent_hand_scaling",
    ),
    BondRank.R5: (
        "capstone_burnt_commitment",
        "aggressively_optimize_compatible_build_around_burnt",
        "abandon_only_for_survival_or_clearly_superior_composition",
    ),
}


@dataclass(frozen=True)
class BurntBondContext:
    """Compatibility context for selecting the hand-leveling target."""

    target_hand: str | None = None
    discards_per_round: int | None = None


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _blue_seal_contribution(state: Any) -> float:
    count = sum(
        1
        for card in _owned_deck(state)
        if str(getattr(card, "seal", "") or "").strip().lower() == "blue"
    )
    if count <= 0:
        return 0.0
    if count == 1:
        return 1.0
    if count == 2:
        return 3.0
    if count == 3:
        return 5.0
    return 6.0


def _target_level_contribution(state: Any, target_hand: str) -> float:
    levels = getattr(state, "hand_levels", {}) or {}
    level = int(levels.get(target_hand, 1) or 1)
    if level <= 1:
        return 0.0
    if level <= 3:
        return 1.0
    if level <= 6:
        return 3.0
    if level <= 10:
        return 5.0
    return 7.0


def _extra_discard_contribution(context: BurntBondContext) -> float:
    if context.discards_per_round is None:
        return 0.0
    bonus = max(0, int(context.discards_per_round) - 3)
    return float(min(3, bonus))


def _hand_token(value: Any) -> str:
    raw = getattr(value, "value", value)
    return "_".join(
        str(raw or "").strip().upper().replace("-", " ").replace("_", " ").split()
    )


def _hand_play_count(state: Any, target: str) -> int:
    total = 0
    for hand, value in (getattr(state, "hand_play_counts", {}) or {}).items():
        if _hand_token(hand) != target:
            continue
        try:
            total += max(0, int(value or 0))
        except (TypeError, ValueError):
            continue
    return total


def select_burnt_target_hand(state: Any, requested: str | None = None) -> str:
    """Select a repeatable target for hand-level development from public evidence."""
    normalized = _hand_token(requested)
    if normalized in BURNT_SUPPORTED_TARGETS:
        return normalized

    levels = getattr(state, "hand_levels", {}) or {}

    def evidence(target: str) -> tuple[int, int, int]:
        level = int(levels.get(target, 1) or 1)
        plays = _hand_play_count(state, target)
        default_priority = 1 if target == "HIGH_CARD" else 0
        return level, plays, default_priority

    return max(BURNT_SUPPORTED_TARGETS, key=evidence)


def _rank_for(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (
        BondRank.R1,
        BondRank.R2,
        BondRank.R3,
        BondRank.R4,
        BondRank.R5,
    ):
        if total >= BURNT_RANK_THRESHOLDS[candidate]:
            rank = candidate
        else:
            return rank, BURNT_RANK_THRESHOLDS[candidate]
    return BondRank.R5, None


def evaluate_hand_leveling_bond(
    state: Any,
    *,
    context: BurntBondContext | None = None,
) -> BondDevelopment:
    """Evaluate persistent hand-level development from public run mechanics."""

    context = context or BurntBondContext()
    target_hand = select_burnt_target_hand(state, context.target_hand)
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    has_discard_leveling = components_have_mechanic(jokers, DISCARD_HAND_LEVELING)
    has_probabilistic_leveling = components_have_mechanic(jokers, PROBABILISTIC_HAND_LEVELING)

    if has_discard_leveling:
        parts.append(BondContribution("Discard hand-level engine", 8.0))

    if has_discard_leveling or has_probabilistic_leveling:
        for _copy_engine in components_with_mechanic(jokers, HAND_LEVEL_COPY):
            parts.append(BondContribution("Copyable hand-level engine", 5.0))

    if has_probabilistic_leveling:
        parts.append(BondContribution("Probabilistic hand-level engine", 4.0))

    vouchers = list(getattr(state, "vouchers", ()) or ())
    if components_have_mechanic(vouchers, PLANET_PACK_TARGETING):
        parts.append(BondContribution("Planet targeting access", 4.0))

    blue_seals = _blue_seal_contribution(state)
    if blue_seals > 0.0:
        parts.append(BondContribution("Blue Seal infrastructure", blue_seals))

    target_level = _target_level_contribution(state, target_hand)
    if target_level > 0.0:
        parts.append(BondContribution(f"{target_hand} permanent specialization", target_level))

    # Extra discards support the discard-based hand-level mechanic specifically.
    if has_discard_leveling:
        extra_discards = _extra_discard_contribution(context)
        if extra_discards > 0.0:
            parts.append(BondContribution("Extra discard capacity", extra_discards))

    total = sum(part.value for part in parts)
    rank, next_threshold = _rank_for(total)
    return BondDevelopment(
        bond_id=HAND_LEVELING_BOND_ID,
        unlocked=total > 0.0,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target=target_hand,
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


# Temporary callable alias for production/tests that still import the legacy name.
def evaluate_burnt_bond(
    state: Any,
    *,
    context: BurntBondContext | None = None,
) -> BondDevelopment:
    return evaluate_hand_leveling_bond(state, context=context)
