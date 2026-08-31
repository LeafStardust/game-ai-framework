from __future__ import annotations

"""Compatibility surface for native Eye/Mouth D1 constraints.

Exact Eye/Mouth candidate constraints and Mouth discard evidence now live in the
canonical D1 path through :mod:`games.balatro.live.boss_hand_constraints` and
``StrategyAwareLiveHandActionPolicy``. This module intentionally performs no class
mutation.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS
from games.balatro.live.boss_hand_constraints import (
    MOUTH_FORCED_STRUCTURE_FIT,
    MOUTH_REDRAW_WIDTH_FIT,
    MOUTH_STRUCTURE_EPSILON,
    eye_filter as _eye_filter,
    mouth_discard_fit as _mouth_discard_fit,
    mouth_discard_only_decision as _mouth_discard_only_decision,
    mouth_filter as _mouth_filter,
    mouth_locked_hand as _mouth_locked_hand,
    mouth_retained_structure as _mouth_retained_structure,
    mouth_zero_score_play_recovery as _mouth_zero_score_play_recovery,
    plan_clear_probability as _plan_clear_probability,
)


def _psychic_filter(state, plans):
    del state
    return tuple(plans)


def _hand_type(policy, state, plan) -> str:
    from games.balatro.live.boss_hand_constraints import _hand_type as native_hand_type

    return native_hand_type(policy, state, plan)


def _mouth_forced_discard(policy, state, plans, decision):
    """Legacy pure selector retained only for deterministic compatibility tests."""
    forced = _mouth_locked_hand(state)
    if forced is None or decision.action.name != DISCARD_CARDS:
        return decision

    discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
    if not discards:
        return decision

    def structure(plan) -> float:
        return _mouth_retained_structure(policy, state, plan.action, forced)

    current_plan = getattr(decision, "selected_plan", None)
    if current_plan is None:
        return decision
    selected_structure = structure(current_plan)
    selected_probability = _plan_clear_probability(current_plan)
    tolerance = float(
        getattr(
            getattr(decision, "thresholds", None),
            "safe_clear_probability_tolerance",
            0.0,
        )
        or 0.0
    )
    equivalent = tuple(
        plan
        for plan in discards
        if structure(plan) + policy.EPSILON >= selected_structure
        and _plan_clear_probability(plan) + tolerance + policy.EPSILON >= selected_probability
    )
    if not equivalent:
        return decision

    selected = max(
        equivalent,
        key=lambda plan: (
            _plan_clear_probability(plan),
            structure(plan),
            len(tuple(getattr(plan.action, "cards", ()) or ())),
            float(policy.evaluator.evaluate(state, plan.action)),
            policy._within_type_key(plan),
        ),
    )
    if selected.action.cards == decision.action.cards:
        return decision
    value = float(policy.evaluator.evaluate(state, selected.action))
    return replace(
        decision,
        mode="PACE_RECOVERY",
        action=selected.action,
        selected_plan=selected,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=value,
        confidence=max(
            float(getattr(decision, "confidence", 0.0) or 0.0),
            _plan_clear_probability(selected),
        ),
        rationale=(
            f"The Mouth is locked to {forced}; forced-hand feasibility overrides unrelated Bond targets",
            f"retained {forced} structure={structure(selected):.3f}; redraw width={len(selected.action.cards)}",
            "legacy compatibility helper only; production uses candidate evidence",
            *decision.rationale,
        ),
    )


def install_boss_hand_constraint_policy() -> None:
    """Compatibility no-op; Eye/Mouth behavior is native to canonical D1."""
    return None


__all__ = [
    "MOUTH_FORCED_STRUCTURE_FIT",
    "MOUTH_REDRAW_WIDTH_FIT",
    "MOUTH_STRUCTURE_EPSILON",
    "_eye_filter",
    "_hand_type",
    "_mouth_discard_fit",
    "_mouth_discard_only_decision",
    "_mouth_filter",
    "_mouth_forced_discard",
    "_mouth_locked_hand",
    "_mouth_retained_structure",
    "_mouth_zero_score_play_recovery",
    "_plan_clear_probability",
    "_psychic_filter",
    "install_boss_hand_constraint_policy",
]
