from __future__ import annotations

"""Scope Red/White safe-pace action authority to the production D1 policy.

The bounded search schedule is installed separately by
``safe_pace_optimization_policy``. This module owns only the production
``StrategyAwareLiveHandActionPolicy`` survival invariant; it no longer patches or
restores base policy classes as an install-order side effect.

The scoped production wrapper may choose the safe-pace action class, but canonical
D1 full-blind plan quality remains authoritative when selecting within that class.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _projected_score(policy, state, plan) -> tuple[float, object]:
    projection = policy.evaluator.project_play(state, plan.action)
    return float(projection.expected_hand_score), projection


def _deterministic_immediate_clear(plan, projection, score: float, remaining: float, epsilon: float) -> bool:
    if score + epsilon < remaining:
        return False
    probability = getattr(projection, "clear_probability", None)
    if probability is not None:
        return float(probability) >= 1.0 - epsilon
    outcomes = getattr(projection, "outcomes", None)
    if outcomes:
        try:
            return min(float(outcome.score) for outcome in outcomes) + epsilon >= remaining
        except (AttributeError, TypeError, ValueError):
            pass
    return bool(
        int(getattr(plan, "horizon", 0) or 0) <= 1
        and bool(getattr(plan, "exact", False))
        and float(plan.value.clear_probability) >= 1.0 - epsilon
    )


def install_safe_pace_scope_correction() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_safe_pace_scope_corrected", False):
        return

    original_strategy_decide = StrategyAwareLiveHandActionPolicy.decide

    def safe_strategy_decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        # Let the established strategy-aware policy establish its normal ranking
        # context/rationale first. We then override only when its chosen action
        # violates the safe-pace survival invariant.
        baseline = original_strategy_decide(self, state, plans, **kwargs)
        plays = [plan for plan in plans if plan.action.name == PLAY_CARDS]
        discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
        if not plays:
            return baseline

        pace_target = self._pace_target(state)
        hands_left = max(1, int(getattr(state, "hands_remaining", 1) or 1))
        remaining = max(0.0, pace_target * hands_left)
        projected = {id(plan): _projected_score(self, state, plan) for plan in plays}
        scores = {key: value[0] for key, value in projected.items()}
        best_play = max(plays, key=self._within_type_key)
        best_immediate = max(plays, key=lambda plan: scores[id(plan)])
        best_score = scores[id(best_immediate)]
        best_ratio = self._pace_ratio(best_score, pace_target)

        old_ranking_state = getattr(self, "_ranking_state", None)
        try:
            if hasattr(self, "_ranking_state"):
                self._ranking_state = state

            immediate_clears = [
                plan
                for plan in plays
                if _deterministic_immediate_clear(
                    plan,
                    projected[id(plan)][1],
                    scores[id(plan)],
                    remaining,
                    self.EPSILON,
                )
            ]
            if immediate_clears:
                selected = max(immediate_clears, key=self._safe_equivalent_clear_key)
                selected_score = scores[id(selected)]
                return replace(
                    baseline,
                    mode=CLEAR_PATH,
                    action=selected.action,
                    selected_plan=selected,
                    best_play=best_play,
                    best_discard=max(discards, key=self._within_type_key) if discards else None,
                    pace_target=pace_target,
                    best_play_immediate_score=best_score,
                    best_play_pace_ratio=best_ratio,
                    selected_immediate_score=selected_score,
                    selected_pace_ratio=self._pace_ratio(selected_score, pace_target),
                    selected_fallback_value=None,
                    clear_path_candidates=len(immediate_clears),
                    sampled_clear_path_confirmed=False,
                    setup_discard_consensus=False,
                    confidence=1.0,
                    rationale=(
                        "safe-pace production policy: current hand deterministically clears the blind",
                        "among deterministic clears, canonical D1 survival/resource ordering remains authoritative",
                        "multi-step engineered clear probability cannot override current-hand survival pacing",
                        *baseline.rationale,
                    ),
                )

            pace_plays = [
                plan
                for plan in plays
                if self._pace_ratio(scores[id(plan)], pace_target) + self.EPSILON
                >= self.thresholds.pace_ratio_floor
            ]
            if pace_plays:
                selected = max(
                    pace_plays,
                    key=lambda plan: self._pace_play_key(
                        plan,
                        self._pace_ratio(scores[id(plan)], pace_target),
                    ),
                )
                selected_score = scores[id(selected)]
                selected_ratio = self._pace_ratio(selected_score, pace_target)
                return replace(
                    baseline,
                    mode=PACE_PLAY,
                    action=selected.action,
                    selected_plan=selected,
                    best_play=best_play,
                    best_discard=max(discards, key=self._within_type_key) if discards else None,
                    pace_target=pace_target,
                    best_play_immediate_score=best_score,
                    best_play_pace_ratio=best_ratio,
                    selected_immediate_score=selected_score,
                    selected_pace_ratio=selected_ratio,
                    selected_fallback_value=None,
                    clear_path_candidates=0,
                    sampled_clear_path_confirmed=False,
                    setup_discard_consensus=False,
                    confidence=self._pace_confidence(selected_ratio),
                    rationale=(
                        "safe-pace production policy: choose among current hands meeting remaining-score / hands-left pace",
                        "canonical D1 full-blind clear probability and plan quality rank pace-qualified plays",
                        "equal-safety held-resource and Bond strategy tie-breaks remain subordinate to survival",
                        *baseline.rationale,
                    ),
                )

            if discards and int(getattr(state, "discards_remaining", 0) or 0) > 0:
                selected = max(
                    discards,
                    key=lambda plan: (
                        *self._within_type_key(plan),
                        float(self.evaluator.evaluate(state, plan.action)),
                    ),
                )
                selected_value = float(self.evaluator.evaluate(state, selected.action))
                consensus = bool(kwargs.get("setup_discard_consensus", False))
                rationale = [
                    "safe-pace production policy: no current play meets remaining-score / hands-left pace",
                    "a legal discard remains, so do not burn a scoring hand below pace",
                    "canonical D1 full-blind plan quality ranks discard candidates before local discard heuristic",
                ]
                if consensus:
                    rationale.append("deep adaptive searches also agree on the setup discard")
                return replace(
                    baseline,
                    mode=PACE_RECOVERY,
                    action=selected.action,
                    selected_plan=selected,
                    best_play=best_play,
                    best_discard=max(discards, key=self._within_type_key),
                    pace_target=pace_target,
                    best_play_immediate_score=best_score,
                    best_play_pace_ratio=best_ratio,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=selected_value,
                    clear_path_candidates=0,
                    sampled_clear_path_confirmed=False,
                    setup_discard_consensus=consensus,
                    confidence=0.75 if consensus else 0.60,
                    rationale=tuple(rationale) + baseline.rationale,
                )

            # No discard remains; preserve canonical D1 full-blind recovery quality.
            selected = best_play
            selected_score = scores[id(selected)]
            selected_ratio = self._pace_ratio(selected_score, pace_target)
            return replace(
                baseline,
                mode=PACE_RECOVERY,
                action=selected.action,
                selected_plan=selected,
                best_play=best_play,
                best_discard=None,
                pace_target=pace_target,
                best_play_immediate_score=best_score,
                best_play_pace_ratio=best_ratio,
                selected_immediate_score=selected_score,
                selected_pace_ratio=selected_ratio,
                selected_fallback_value=float(self.evaluator.evaluate(state, selected.action)),
                clear_path_candidates=0,
                sampled_clear_path_confirmed=False,
                setup_discard_consensus=False,
                confidence=0.40,
                rationale=(
                    "safe-pace production policy: no current play meets pace and no discard remains",
                    "forced recovery uses the strongest full-blind D1 plan; immediate score is secondary",
                    *baseline.rationale,
                ),
            )
        finally:
            if hasattr(self, "_ranking_state"):
                self._ranking_state = old_ranking_state

    StrategyAwareLiveHandActionPolicy.decide = safe_strategy_decide
    StrategyAwareLiveHandActionPolicy._safe_pace_scope_corrected = True
