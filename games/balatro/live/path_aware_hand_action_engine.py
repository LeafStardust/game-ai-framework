from __future__ import annotations

from dataclasses import dataclass, is_dataclass, replace
from time import perf_counter

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.d1_hook_search_budget_policy import effective_d1_search_seconds
from games.balatro.live.adaptive_search import (
    AdaptiveRecommendationSummary,
    stable_discard_consensus,
)
from games.balatro.live.blind_clear_planner import (
    LiveBlindPlan,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
    HandActionDecision,
    LiveHandActionDecisionEngine as _BaseLiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_health import LiveStrategyHealth, evaluate_live_strategy_health
from games.balatro.safe_pace_optimization_policy import _safe_search_schedule
from games.balatro.safe_pace_timeout_patch import _bounded_structural_timeout_fallback


@dataclass(frozen=True)
class D1LatencyBreakdown:
    """Non-overlapping wall-clock accounting for one authoritative D1 decision."""

    total: float
    base_policy: float
    adaptive_search: float
    confirmation_search: float
    immediate_fallback_search: float
    adaptive_authority: float
    consensus_recovery: float
    strategy_health: float
    residual: float


def _build_d1_latency_breakdown(
    *,
    total: float,
    base_elapsed: float,
    adaptive_search: float,
    confirmation_search: float,
    immediate_fallback_search: float,
    adaptive_authority: float,
    consensus_recovery: float,
    strategy_health: float,
) -> D1LatencyBreakdown:
    """Convert nested measurements into conservative non-overlapping buckets."""
    adaptive_search = max(0.0, float(adaptive_search))
    confirmation_search = max(0.0, float(confirmation_search))
    immediate_fallback_search = max(0.0, float(immediate_fallback_search))
    adaptive_authority = max(0.0, float(adaptive_authority))
    consensus_recovery = max(0.0, float(consensus_recovery))
    strategy_health = max(0.0, float(strategy_health))
    total = max(0.0, float(total))
    base_policy = max(
        0.0,
        float(base_elapsed)
        - adaptive_search
        - confirmation_search
        - immediate_fallback_search,
    )
    known = (
        base_policy
        + adaptive_search
        + confirmation_search
        + immediate_fallback_search
        + adaptive_authority
        + consensus_recovery
        + strategy_health
    )
    return D1LatencyBreakdown(
        total=total,
        base_policy=base_policy,
        adaptive_search=adaptive_search,
        confirmation_search=confirmation_search,
        immediate_fallback_search=immediate_fallback_search,
        adaptive_authority=adaptive_authority,
        consensus_recovery=consensus_recovery,
        strategy_health=strategy_health,
        residual=max(0.0, total - known),
    )


class PathAwareLiveHandActionDecisionEngine(_BaseLiveHandActionDecisionEngine):
    """D1 engine that preserves adaptive evidence without creating a second controller.

    The core engine already performs the expensive public-state clear-path search.
    When several deepest adaptive passes agree on the same setup discard but cannot
    cross the credible-clear threshold, this extension preserves that setup identity
    during recovery instead of silently switching to a different one-step discard.

    Completed root plan sets are also retained until the decision returns. If the
    wall-clock budget expires after at least one canonical root search completed,
    timeout reuses that completed evidence through the canonical D1 policy rather
    than switching to either a second structural controller or raw planner ordering.
    The structural fallback remains only as the emergency legal-action path when no
    canonical root evidence completed or the public hand itself is unavailable.

    Normal post-policy adaptive evidence is subordinate to the action class selected
    by the canonical production policy. A pace-qualified Play cannot be replaced
    after arbitration, and recovery evidence may refine only within the already
    selected Play/Discard class. This keeps one controller responsible for D1.

    After the final D1 action is fixed, the engine evaluates the frozen 46-Bond
    composition and Build Health from that selected plan. The result is exposed as
    ``last_strategy_health`` for strategy/shop/telemetry consumers. It is deliberately
    downstream of D1 selection and cannot change the survival-ranked action.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._record_adaptive_roots = False
        self._record_d1_latency = False
        self._adaptive_root_history: list[
            tuple[AdaptiveRecommendationSummary, LiveBlindPlan]
        ] = []
        self._adaptive_plan_history: list[tuple[LiveBlindPlan, ...]] = []
        self._d1_adaptive_search_seconds = 0.0
        self._d1_confirmation_search_seconds = 0.0
        self._d1_immediate_fallback_seconds = 0.0
        self.last_strategy_health: LiveStrategyHealth | None = None
        self.last_latency_breakdown: D1LatencyBreakdown | None = None

    def _search_schedule(self, state):
        """Apply the production safe-pace search budget without mutating base D1."""
        return _safe_search_schedule(
            hands_remaining=int(state.hands_remaining),
            discards_remaining=int(state.discards_remaining),
            max_horizon=self.max_horizon,
            max_nodes=self.max_search_nodes,
        )

    def rank_plans(self, state, *, planner=None):
        started = perf_counter()
        confirmation = planner is not None and hasattr(
            planner,
            "_confirmation_root_action",
        )
        try:
            plans = super().rank_plans(state, planner=planner)
        finally:
            if self._record_d1_latency:
                elapsed = perf_counter() - started
                if confirmation:
                    self._d1_confirmation_search_seconds += elapsed
                else:
                    self._d1_adaptive_search_seconds += elapsed
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

    def _rank_immediate_plans(self, state):
        started = perf_counter()
        try:
            if self.max_search_seconds is not None and self._search_deadline is not None:
                raise PlannerSearchBudgetExceeded(
                    "skip projected immediate fallback under hard D1 budget"
                )
            return super()._rank_immediate_plans(state)
        finally:
            if self._record_d1_latency:
                self._d1_immediate_fallback_seconds += perf_counter() - started

    def decide(self, state) -> HandActionDecision:
        total_started = perf_counter()
        self._adaptive_root_history = []
        self._adaptive_plan_history = []
        self._d1_adaptive_search_seconds = 0.0
        self._d1_confirmation_search_seconds = 0.0
        self._d1_immediate_fallback_seconds = 0.0
        self._record_adaptive_roots = True
        self._record_d1_latency = True
        self.last_strategy_health = None
        self.last_latency_breakdown = None
        configured_search_seconds = self.max_search_seconds
        self.max_search_seconds = effective_d1_search_seconds(
            state,
            configured_search_seconds,
        )
        base_started = perf_counter()
        try:
            decision = super().decide(state)
        finally:
            base_elapsed = perf_counter() - base_started
            self.max_search_seconds = configured_search_seconds
            self._record_adaptive_roots = False
            self._record_d1_latency = False

        stage_started = perf_counter()
        decision = self._apply_adaptive_authority(state, decision)
        adaptive_authority = perf_counter() - stage_started

        stage_started = perf_counter()
        decision = self._apply_consensus_recovery(state, decision)
        consensus_recovery = perf_counter() - stage_started

        stage_started = perf_counter()
        self.last_strategy_health = evaluate_live_strategy_health(
            state,
            selected_plan=decision.selected_plan,
        )
        strategy_health = perf_counter() - stage_started

        breakdown = _build_d1_latency_breakdown(
            total=perf_counter() - total_started,
            base_elapsed=base_elapsed,
            adaptive_search=self._d1_adaptive_search_seconds,
            confirmation_search=self._d1_confirmation_search_seconds,
            immediate_fallback_search=self._d1_immediate_fallback_seconds,
            adaptive_authority=adaptive_authority,
            consensus_recovery=consensus_recovery,
            strategy_health=strategy_health,
        )
        self.last_latency_breakdown = breakdown
        if is_dataclass(decision) and hasattr(decision, "rationale"):
            decision = replace(
                decision,
                rationale=(
                    *decision.rationale,
                    (
                        "D1 latency "
                        f"total={breakdown.total:.6f}s "
                        f"base_policy={breakdown.base_policy:.6f}s "
                        f"adaptive_search={breakdown.adaptive_search:.6f}s "
                        f"confirmation_search={breakdown.confirmation_search:.6f}s "
                        f"immediate_fallback_search={breakdown.immediate_fallback_search:.6f}s "
                        f"adaptive_authority={breakdown.adaptive_authority:.6f}s "
                        f"consensus_recovery={breakdown.consensus_recovery:.6f}s "
                        f"strategy_health={breakdown.strategy_health:.6f}s "
                        f"residual={breakdown.residual:.6f}s"
                    ),
                ),
            )
        return decision

    def _structural_timeout_fallback(
        self,
        state,
        *,
        search_attempts,
    ) -> HandActionDecision:
        """Reuse completed D1 evidence without bypassing the final D1 arbiter.

        A wall-clock deadline may stop additional search. It does not promote the
        planner's root ordering into final Play-vs-Discard authority. When complete
        public hand state is available, the latest completed plan set is therefore
        passed back through ``LiveHandActionPolicy``. Only synthetic/incomplete states
        without a visible hand retain the old raw-ranking behavior because the policy
        cannot recompute literal immediate pace/recovery evidence from missing state.
        """
        if not self._adaptive_plan_history:
            return _bounded_structural_timeout_fallback(
                self,
                state,
                search_attempts=search_attempts,
            )

        plans = self._adaptive_plan_history[-1]
        plays = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
        if not plays:
            return _bounded_structural_timeout_fallback(
                self,
                state,
                search_attempts=search_attempts,
            )

        summaries = tuple(summary for summary, _ in self._adaptive_root_history)
        consensus = stable_discard_consensus(
            summaries,
            minimum_agreement=self.policy.thresholds.setup_discard_consensus_agreement,
        )

        if hasattr(state, "hand"):
            decision = self.policy.decide(
                state,
                plans,
                search_attempts=tuple(search_attempts),
                setup_discard_consensus=bool(consensus),
            )
            return replace(
                decision,
                rationale=(
                    "D1 wall-clock budget exhausted after a canonical adaptive root completed",
                    "reuse the latest completed plan set through the canonical Play-vs-Discard arbiter",
                    *decision.rationale,
                    "take only this action, then re-observe and replan",
                ),
            )

        selected = plans[0]
        discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
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

        setup_consensus = bool(consensus and selected.action.name == DISCARD_CARDS)
        rationale = [
            "D1 wall-clock budget exhausted after a canonical adaptive root completed",
            "public hand is unavailable; reuse the latest completed root rather than fabricate immediate policy evidence",
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
        """Use deeper completed evidence only within the finalized recovery class.

        Production policy owns Play-vs-Discard survival arbitration. In particular,
        a pace-qualified Play is final: a post-policy wrapper must not replace it
        with an engineered deeper line. When the policy is already in recovery,
        however, a materially superior completed root may refine the particular
        candidate so long as it stays in the same Play/Discard class.
        """
        if decision.mode in {CLEAR_PATH, PACE_PLAY} or not self._adaptive_root_history:
            return decision

        search_plan = self._adaptive_root_history[-1][1]
        if search_plan.action.name != decision.action.name:
            return decision
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
                "completed adaptive root materially improves the finalized recovery class",
                f"action class={search_plan.action.name}; clear probability={selected_probability:.3f}->{search_probability:.3f}",
                f"expected score={selected_score:.1f}->{search_score:.1f}; exact={search_plan.exact}",
                "production policy remains the sole Play-vs-Discard survival arbiter",
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
