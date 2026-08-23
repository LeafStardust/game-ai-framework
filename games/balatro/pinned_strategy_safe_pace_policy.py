from __future__ import annotations

"""Restore strategy-aware ranking inside the final safe-pace D1 chooser.

The safety-first pace patch intentionally prefers current scoring strength, but its
PACE_PLAY branch historically selected the single highest projected score directly.
That bypassed StrategyAwareLiveHandActionPolicy._pace_play_key and could throw away
held engine cards even when another play was essentially score-equivalent.

This layer does not weaken survival. It first identifies the best immediate score
among already pace-qualified plays, then admits strategy tie-breaking only inside a
narrow 98% score-equivalence band. A materially stronger scoring line remains
mandatory.
"""

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy


PACE_STRATEGY_EQUIVALENCE_RATIO = 0.98


def pace_strategy_equivalent_plans(
    policy,
    state,
    plans,
    *,
    projected_scores: dict[int, float] | None = None,
):
    """Return pace-qualified plays close enough to best score for strategy ranking."""
    plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
    if not plays:
        return ()
    pace_target = float(policy._pace_target(state))
    scores = projected_scores or {
        id(plan): float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        for plan in plays
    }
    pace_qualified = tuple(
        plan
        for plan in plays
        if policy._pace_ratio(scores[id(plan)], pace_target) + policy.EPSILON
        >= policy.thresholds.pace_ratio_floor
    )
    if not pace_qualified:
        return ()
    best_score = max(scores[id(plan)] for plan in pace_qualified)
    minimum_score = max(
        pace_target * float(policy.thresholds.pace_ratio_floor),
        best_score * PACE_STRATEGY_EQUIVALENCE_RATIO,
    )
    return tuple(
        plan for plan in pace_qualified
        if scores[id(plan)] + policy.EPSILON >= minimum_score
    )


def select_strategy_safe_pace_plan(policy, state, plans, projected_scores):
    """Select with dynamic strategy-aware pace key only inside the safety band."""
    equivalent = pace_strategy_equivalent_plans(
        policy,
        state,
        plans,
        projected_scores=projected_scores,
    )
    if not equivalent:
        return None
    pace_target = float(policy._pace_target(state))
    return max(
        equivalent,
        key=lambda plan: policy._pace_play_key(
            plan,
            policy._pace_ratio(projected_scores[id(plan)], pace_target),
        ),
    )


def install_pinned_strategy_safe_pace_policy() -> None:
    if getattr(LiveHandActionPolicy, "_pinned_strategy_safe_pace_installed", False):
        return
    original_decide = LiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        decision = original_decide(self, state, plans, **kwargs)
        if decision.mode != PACE_PLAY:
            return decision
        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        if len(plays) < 2:
            return decision
        scores = {
            id(plan): float(self.evaluator.project_play(state, plan.action).expected_hand_score)
            for plan in plays
        }
        equivalent = pace_strategy_equivalent_plans(
            self,
            state,
            plays,
            projected_scores=scores,
        )
        if len(equivalent) < 2:
            return decision
        selected = select_strategy_safe_pace_plan(self, state, equivalent, scores)
        if selected is None or selected is decision.selected_plan:
            return decision
        selected_score = scores[id(selected)]
        selected_ratio = self._pace_ratio(selected_score, decision.pace_target)
        best_score = max(scores[id(plan)] for plan in plays)
        return replace(
            decision,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=selected_score,
            selected_pace_ratio=selected_ratio,
            confidence=self._pace_confidence(selected_ratio),
            rationale=(
                *decision.rationale,
                f"strategy-aware safe-equivalent pace band: selected score={selected_score:.3f}, best={best_score:.3f}, floor={PACE_STRATEGY_EQUIVALENCE_RATIO:.3f}x best",
                "pinned strategy may break only near-equivalent pace ties; materially stronger scoring remains authoritative",
            ),
        )

    LiveHandActionPolicy.decide = decide
    LiveHandActionPolicy._pinned_strategy_safe_pace_installed = True
