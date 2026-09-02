from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from games.balatro.bonds.contributions import component_contribution, finalize_development, state_contribution
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank
from games.balatro.mechanics import (
    DISCARD_HAND_LEVELING,
    HAND_LEVEL_COPY,
    PLANET_PACK_TARGETING,
    PROBABILISTIC_HAND_LEVELING,
    component_has_mechanic,
)

HAND_LEVELING_BOND_ID = "hand_leveling"
BURNT_BOND_ID = HAND_LEVELING_BOND_ID
BURNT_SUPPORTED_TARGETS = frozenset({"HIGH_CARD", "PAIR"})
BURNT_RANK_THRESHOLDS: dict[BondRank, float] = {
    BondRank.R1: 8.0,
    BondRank.R2: 12.0,
    BondRank.R3: 17.0,
    BondRank.R4: 23.0,
    BondRank.R5: 30.0,
}
BURNT_RANK_POLICIES: dict[BondRank, tuple[str, ...]] = {
    BondRank.R1: ("recognize_first_discard_level_value", "default_target_high_card_without_stronger_hand_bond"),
    BondRank.R2: ("reinforce_selected_target_hand", "prefer_targeted_hand_level_infrastructure", "preserve_reasonable_first_discard_access"),
    BondRank.R3: ("actively_shape_resources_around_target_hand", "protect_material_burnt_contributors", "increase_search_value_for_burnt_reinforcement"),
    BondRank.R4: ("eligible_as_power_engine", "activate_first_discard_before_trivial_clear_when_safe", "strongly_prioritize_targeted_permanent_hand_scaling"),
    BondRank.R5: ("capstone_burnt_commitment", "aggressively_optimize_compatible_build_around_burnt", "abandon_only_for_survival_or_clearly_superior_composition"),
}


@dataclass(frozen=True)
class BurntBondContext:
    target_hand: str | None = None
    discards_per_round: int | None = None


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _blue_seal_contribution(state: Any) -> float:
    count = sum(
        1 for card in _owned_deck(state)
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
    return "_".join(str(raw or "").strip().upper().replace("-", " ").replace("_", " ").split())


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


def _source(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    cls = component.__class__.__name__
    return fallback if cls in {"str", "SimpleNamespace"} else cls


def evaluate_hand_leveling_bond(
    state: Any,
    *,
    context: BurntBondContext | None = None,
) -> BondDevelopment:
    """Evaluate persistent hand-level development through the canonical ledger."""
    context = context or BurntBondContext()
    target_hand = select_burnt_target_hand(state, context.target_hand)
    jokers = list(getattr(state, "jokers", ()) or ())
    parts: list[BondContribution] = []

    has_discard_leveling = any(component_has_mechanic(j, DISCARD_HAND_LEVELING) for j in jokers)
    has_probabilistic_leveling = any(component_has_mechanic(j, PROBABILISTIC_HAND_LEVELING) for j in jokers)

    for index, joker in enumerate(jokers):
        if component_has_mechanic(joker, DISCARD_HAND_LEVELING):
            parts.append(component_contribution(
                joker, collection="jokers", index=index,
                label=_source(joker, "Discard hand-level engine"), value=8.0,
                mechanic=DISCARD_HAND_LEVELING,
            ))
        if component_has_mechanic(joker, PROBABILISTIC_HAND_LEVELING):
            parts.append(component_contribution(
                joker, collection="jokers", index=index,
                label=_source(joker, "Probabilistic hand-level engine"), value=4.0,
                mechanic=PROBABILISTIC_HAND_LEVELING,
            ))
        if (has_discard_leveling or has_probabilistic_leveling) and component_has_mechanic(joker, HAND_LEVEL_COPY):
            parts.append(component_contribution(
                joker, collection="jokers", index=index,
                label=_source(joker, "Copyable hand-level engine"), value=5.0,
                mechanic=HAND_LEVEL_COPY,
            ))

    for index, voucher in enumerate(list(getattr(state, "vouchers", ()) or ())):
        if component_has_mechanic(voucher, PLANET_PACK_TARGETING):
            parts.append(component_contribution(
                voucher, collection="vouchers", index=index,
                label=_source(voucher, "Planet targeting access"), value=4.0,
                mechanic=PLANET_PACK_TARGETING,
            ))

    blue_seals = _blue_seal_contribution(state)
    if blue_seals > 0.0:
        parts.append(state_contribution(
            "deck:blue_seal_density", "Blue Seal infrastructure", blue_seals,
            mechanic="blue_seal_density",
        ))

    target_level = _target_level_contribution(state, target_hand)
    if target_level > 0.0:
        parts.append(state_contribution(
            f"hand_level:{target_hand}", f"{target_hand} permanent specialization", target_level,
            mechanic=f"hand_level:{target_hand}",
        ))

    if has_discard_leveling:
        extra_discards = _extra_discard_contribution(context)
        if extra_discards > 0.0:
            parts.append(state_contribution(
                "round:extra_discard_capacity", "Extra discard capacity", extra_discards,
                mechanic="extra_discard_capacity",
            ))

    return finalize_development(
        HAND_LEVELING_BOND_ID,
        parts,
        BURNT_RANK_THRESHOLDS,
        unlocked=bool(parts),
        target=target_hand,
    )


def evaluate_burnt_bond(
    state: Any,
    *,
    context: BurntBondContext | None = None,
) -> BondDevelopment:
    return evaluate_hand_leveling_bond(state, context=context)
