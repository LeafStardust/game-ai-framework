from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.adaptive_search import (
    AdaptiveRecommendationSummary,
    stable_discard_consensus,
)
from games.balatro.live.blind_clear_planner import LiveBlindPlan
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
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

    Completed root plan sets are also retained until the decision returns. If the
    wall-clock budget expires after at least one canonical root search completed,
    timeout returns the best already-computed D1 plan instead of switching to the
    base structural poker-hand/rank heuristic. The structural fallback remains only
    as the emergency legal-action path when no canonical root evidence completed.

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
        self._adaptive_plan_history: list[tuple[LiveBlindPlan, ...]] = []
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
            self._adaptive_plan_history.append(tuple(plans))
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
        self._adaptive_plan_history = []
        self._record_adaptive_roots = True
        self.last_strategy_health = None
        try:
            decision = super().decide(state)
        finally:
            self._record_adaptive_roots = False
        decision = self._apply_adaptive_authority(state, decision)
        decision = self._apply_consensus_recovery(state, decision)
        self.last_strategy_health = evaluate_live_strategy_health(
            state,
            selected_plan=decision.selected_plan,
        )
        return decision

    def _structural_timeout_fallback(
        self,
        state,
        *,
        search_attempts,
    ) -> HandActionDecision:
        """Reuse completed canonical D1 evidence before any structural emergency.

        A wall-clock deadline bounds how much more evidence D1 may compute; it does
        not authorize a different strategy. Normal adaptive root searches are already
        ranked by the canonical full-blind planner objective, so the latest completed
        root remains the best available evidence when a later pass times out.
        """
        if not self._adaptive_plan_history:
            return super()._structural_timeout_fallback(
                state,
                search_attempts=search_attempts,
            )

        plans = self._adaptive_plan_history[-1]
        selected = plans[0]
        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
        if not plays:
            # Canonical D1 normally always has a Play root. If that invariant is
            # ever broken, the base emergency path is safer than fabricating fields.
            return super()._structural_timeout_fallback(
                state,
                search_attempts=search_attempts,
            )

        best_play = plays[0]
        best_discard = discards[0] if discards else None
        probability = float(selected.value.clear_probability)
        exact_clear = bool(selected.exact) and self.policy._meets_clear_floor(selected)
        mode = CLEAR_PATH if exact_clear else PACE_RECOVERY

        confidence = probability
        if not bool(selected.exact):
            confidence = min(confidence, self.policy.SAMPLED_CONFIDENCE_CAP)
        if not exact_clear and confidence <= 0.0:
            confidence = 0.25

        summaries = tuple(summary for summary, _ in self._adaptive_root_history)
        consensus = stable_discard_consensus(
            summaries,
            minimum_agreement=self.policy.thresholds.setup_discard_consensus_agreement,
        )
        setup_consensus = bool(consensus and selected.action.name == DISCARD_CARDS)

        rationale = [
            "D1 wall-clock budget exhausted after a canonical adaptive root completed",
            "reuse the latest completed full-blind D1 ranking; timeout cannot invent a second strategy",
        ]
        if exact_clear:
            rationale.append(
                "the retained root is an exact credible clear and remains authoritative"
            )
        elif probability >= self.policy.thresholds.clear_path_probability_floor:
            rationale.append(
                "the retained sampled clear evidence was not fully confirmed before timeout, so it is kept as best available evidence without being promoted to a confirmed clear"
            )
        else:
            rationale.append(
                "the retained root is the strongest completed recovery/progress line under the canonical planner objective"
            )
        if setup_consensus:
            rationale.append("completed adaptive roots also agree on the selected setup discard")
        rationale.append("take only this action, then re-observe and replan")

        return self.policy._decision(
            mode=mode,
            selected=selected,
            best_play=best_play,
            best_discard=best_discard,
            pace_target=self.policy._pace_target(state),
            best_play_immediate_score=0.0,
            best_play_pace_ratio=0.0,
            selected_immediate_score=None,
            selected_pace_ratio=None,
            selected_fallback_value=None,
            clear_path_candidates=1 if exact_clear else 0,
            sampled_clear_path_confirmed=False,
            setup_discard_consensus=setup_consensus,
            confidence=confidence,
            rationale=tuple(rationale),
            plans=plans,
            search_attempts=tuple(search_attempts),
        )

    def _apply_adaptive_authority(
        self,
        state,
        decision: HandActionDecision,
    ) -> HandActionDecision:
        """Keep a materially superior completed search root as the D1 action.

        The shallow one-step pace policy is a fallback, not a second independent
        controller. Production logs showed it selecting the opposite action from a
        completed exact/deeper root seventeen times. Only material superiority is
        authoritative here; close search estimates still defer to the safer pace
        policy.
        """
        if decision.mode == CLEAR_PATH or not self._adaptive_root_history:
            return decision

        search_plan = self._adaptive_root_history[-1][1]
        if self._action_signature(state, search_plan.action) == self._action_signature(
            state,
            decision.action,
        ):
            return decision

        search_value = search_plan.value
        selected_value = decision.selected_plan.value
        search_probability = float(search_value.clear_probability)
        selected_probability = float(selected_value.clear_probability)
        search_score = float(search_value.expected_score)
        selected_score = float(selected_value.expected_score)

        probability_gain = search_probability - selected_probability
        score_gain = search_score - selected_score
        material_probability = probability_gain >= 0.05
        material_score = (
            probability_gain >= -0.01
            and score_gain >= max(25.0, abs(selected_score) * 0.15)
        )
        exact_upgrade = (
            bool(search_plan.exact)
            and not bool(decision.selected_plan.exact)
            and probability_gain >= -0.01
            and score_gain >= 0.0
        )
        if not (material_probability or material_score or exact_upgrade):
            return decision

        plans = list(decision.plans)
        if not any(
            self._action_signature(state, plan.action)
            == self._action_signature(state, search_plan.action)
            for plan in plans
        ):
            plans.append(search_plan)

        mode = (
            CLEAR_PATH
            if bool(search_plan.exact)
            and search_probability + self.policy.EPSILON
            >= self.policy.thresholds.clear_path_probability_floor
            else PACE_RECOVERY
        )
        confidence = max(float(decision.confidence), search_probability)
        if not search_plan.exact:
            confidence = min(confidence, self.policy.SAMPLED_CONFIDENCE_CAP)
        return replace(
            decision,
            mode=mode,
            action=search_plan.action,
            selected_plan=search_plan,
            best_play=(
                search_plan
                if search_plan.action.name != DISCARD_CARDS
                else decision.best_play
            ),
            best_discard=(
                search_plan
                if search_plan.action.name == DISCARD_CARDS
                else decision.best_discard
            ),
            selected_immediate_score=None,
            selected_pace_ratio=None,
            selected_fallback_value=None,
            confidence=confidence,
            rationale=(
                "completed adaptive root is materially superior to the one-step pace fallback",
                f"action={decision.action.name}->{search_plan.action.name}; clear probability={selected_probability:.3f}->{search_probability:.3f}",
                f"expected score={selected_score:.1f}->{search_score:.1f}; exact={search_plan.exact}",
                "one controller owns the final D1 action; completed search evidence is not logged and then ignored",
            ),
            candidate_count=len(plans),
            plans=tuple(plans),
        )

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

        build_evaluator = getattr(self.policy, "build_evaluator", None)
        if build_evaluator is not None:
            preservation = build_evaluator.evaluate_preservation(state, setup_plan.action)
            rationale.extend(preservation.rationale)
            build_evaluator.reset_cache()

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
