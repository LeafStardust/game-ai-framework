from __future__ import annotations

"""Compatibility helpers for canonical strategy-safe pace semantics.

Production safe-pace refinement now lives in ``StrategyAwareLiveHandActionPolicy``.
This module installs nothing; it preserves pure helper-level regression contracts.
"""

from games.balatro.actions import PLAY_CARDS

PACE_STRATEGY_EQUIVALENCE_RATIO = 0.98


def pace_strategy_equivalent_plans(policy, state, plans, *, projected_scores):
    del state
    plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
    if not plays:
        return ()
    pace_target = float(policy._pace_target(None))
    qualified = tuple(
        plan
        for plan in plays
        if policy._pace_ratio(float(projected_scores[id(plan)]), pace_target) + policy.EPSILON
        >= float(policy.thresholds.pace_ratio_floor)
    )
    if not qualified:
        return ()
    best_score = max(float(projected_scores[id(plan)]) for plan in qualified)
    minimum = max(
        pace_target * float(policy.thresholds.pace_ratio_floor),
        best_score * PACE_STRATEGY_EQUIVALENCE_RATIO,
    )
    return tuple(
        plan
        for plan in qualified
        if float(projected_scores[id(plan)]) + policy.EPSILON >= minimum
    )


def select_strategy_safe_pace_plan(policy, state, plans, projected_scores):
    del state
    plans = tuple(plans)
    if not plans:
        return None
    pace_target = float(policy._pace_target(None))
    return max(
        plans,
        key=lambda plan: policy._pace_play_key(
            plan,
            policy._pace_ratio(float(projected_scores[id(plan)]), pace_target),
        ),
    )


__all__ = [
    "PACE_STRATEGY_EQUIVALENCE_RATIO",
    "pace_strategy_equivalent_plans",
    "select_strategy_safe_pace_plan",
]
