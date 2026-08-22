from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS
from games.balatro.live.adaptive_search import AdaptiveRecommendationSummary
from games.balatro.live.blind_clear_planner import LiveBlindPlan
from games.balatro.live.hand_action_policy import (
    PACE_RECOVERY,
    HandActionDecision,
    LiveHandActionDecisionEngine as _BaseLiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_health import LiveStrategyHealth, evaluate_live_strategy_health


class PathAwareLiveHandActionDecisionEngine(_BaseLiveHandActionDecisionEngine):
    """D1 engine that preserves stable adaptive setup-discard intent in recovery.

    The core engine already performs the expensive public-state clear-path search.
    When several deepest adaptive passes agree on the same setup discard but cannot
    cross the credible-clear threshold, the base fallback currently throws that
    action identity away and reselects recovery from one-step heuristic values.

    This extension records only normal adaptive root recommendations. Confirmation
    passes are excluded. If the core decision reaches ``PACE_RECOVERY`` with stable
    discard consensus, D1 keeps the agreed setup discard instead of silently
    switching to a different one-step recovery action. ``CLEAR_PATH`` and
    ``PACE_PLAY`` behavior is unchanged.

    After the final D1 action is fixed, the engine evaluates the frozen 46-Bond
    composition and Build Health from that selected plan. The result is exposed as
    ``last_strategy_health`` for strategy/shop/telemetry consumers. It is deliberately
    downstream of D1 selection and cannot change the survival-ranked action.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._record_adaptive_roots = False
        self._adaptive_root_history: list[
            tuple[AdaptiveRecommendationSummary, LiveBlindPlan]
        ] = []
        self.last_strategy_health: LiveStrategyHealth | None = None

    def rank_plans(self, state, *, planner=None):
        plans = super().rank_plans(state, planner=planner)
        if (
            self._record_adaptive_roots
            and planner is not None
            and not hasattr(planner, "_confirmation_root_action")
            and plans
        ):
            best = plans[0]
            self._adaptive_root_history.append(
                (
                    AdaptiveRecommendationSummary(
                        action=best.action.name,
                        indices=self._indices(state, best.action),
                        clear_probability=float(best.value.clear_probability),
                        expected_score=float(best.value.expected_score),
                        horizon=int(getattr(planner, "horizon", 0) or 0),
                        intensified=(
                            int(getattr(planner, "max_nodes", 0) or 0) > 5000
                        ),
                    ),
                    best,
                )
            )
        return plans

    def decide(self, state) -> HandActionDecision:
        self._adaptive_root_history = []
        self._record_adaptive_roots = True
        self.last_strategy_health = None
        try:
            decision = super().decide(state)
        finally:
            self._record_adaptive_roots = False
        decision = self._apply_consensus_recovery(state, decision)
        self.last_strategy_health = evaluate_live_strategy_health(
            state,
            selected_plan=decision.selected_plan,
        )
        return decision

    def _apply_consensus_recovery(
        self,
        state,
        decision: HandActionDecision,
    ) -> HandActionDecision:
        if decision.mode != PACE_RECOVERY or not decision.setup_discard_consensus:
            return decision
        if not self._adaptive_root_history:
            return decision

        target_summary = self._adaptive_root_history[-1][0]
        if target_summary.action != DISCARD_CARDS or not target_summary.indices:
            return decision

        setup_plan = next(
            (
                plan
                for summary, plan in reversed(self._adaptive_root_history)
                if summary.action == DISCARD_CARDS
                and summary.indices == target_summary.indices
            ),
            None,
        )
        if setup_plan is None:
            return decision

        target_signature = self._action_signature(state, setup_plan.action)
        if self._action_signature(state, decision.action) == target_signature:
            return decision

        selected_value = self._fallback_value(state, setup_plan)
        other_values = [
            self._fallback_value(state, plan)
            for plan in decision.plans
            if self._action_signature(state, plan.action) != target_signature
        ]
        runner_up = max(other_values, default=selected_value)
        confidence = self.policy._recovery_confidence(
            selected_value - runner_up,
            consensus=True,
        )

        plans = list(decision.plans)
        if not any(
            self._action_signature(state, plan.action) == target_signature
            for plan in plans
        ):
            plans.append(setup_plan)

        rationale = [
            "adaptive search found no credible blind-clear path",
            "no current play reaches the required next-hand pace",
            "deep adaptive searches agree on one setup discard",
            (
                "preserve the modeled recovery path instead of reselecting a "
                "different discard from one-step recovery value"
            ),
        ]
        if (
            int(getattr(state, "discards_remaining", 0))
            <= self.policy.thresholds.low_discard_reserve
        ):
            rationale.append(
                "low discard reserve penalty was recorded without discarding the stable path consensus"
            )

        strategic = getattr(self.policy, "playstyle_evaluator", None)
        if strategic is not None:
            preservation = strategic.evaluate_preservation(state, setup_plan.action)
            playstyle = strategic.evaluate_playstyle(state, setup_plan.action)
            rationale.extend(preservation.rationale)
            rationale.extend(playstyle.rationale)
            strategic.reset_cache()

        return replace(
            decision,
            action=setup_plan.action,
            selected_plan=setup_plan,
            best_discard=setup_plan,
            selected_immediate_score=None,
            selected_pace_ratio=None,
            selected_fallback_value=selected_value,
            setup_discard_consensus=True,
            confidence=confidence,
            rationale=tuple(rationale),
            candidate_count=len(plans),
            plans=tuple(plans),
        )

    def _fallback_value(self, state, plan: LiveBlindPlan) -> float:
        value = float(self.policy.evaluator.evaluate(state, plan.action))
        if plan.action.name != DISCARD_CARDS:
            return value

        if (
            int(getattr(state, "discards_remaining", 0))
            <= self.policy.thresholds.low_discard_reserve
        ):
            value -= self.policy.thresholds.low_discard_fallback_penalty
        if (
            int(getattr(state, "hands_remaining", 0))
            <= self.policy.thresholds.low_hand_reserve
        ):
            value += self.policy.thresholds.low_hand_discard_fallback_bonus
        return value
