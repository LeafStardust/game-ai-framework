from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
)
from games.balatro.live.build_intent_log import (
    BuildIntentLogTracker,
    PreparedBuildIntentLog,
)
from games.balatro.live.hand_action_policy import (
    HandActionThresholds,
    LiveHandActionDecisionEngine,
)
from games.balatro.live.hand_playstyle import BuildAwareLiveHandActionPolicy
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import DefaultShopItemValueEstimator
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy

from .live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
    _indices,
    _search_schedule_mode,
)


@dataclass(frozen=True)
class PlaystyleAutonomousStepDecision(AutonomousStepDecision):
    build_intent: PreparedBuildIntentLog | None = None


class PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
    LiveMemoryInjectedSingleStepRunner
):
    """Production single-step runner with one run-scoped build-intent lifecycle.

    The base runner remains the mechanics/execution implementation. This adapter
    wires one competence-layer playstyle tracker into D1 hand decisions, D2
    Joker/shop valuation, D9 booster choices, structured run logging, and the
    dedicated D3 persistent-voucher shop policy. A supervisor retry creates a fresh
    runner and therefore a fresh playstyle tracker.
    """

    def __init__(self, observer, **kwargs) -> None:
        custom_hand_recommender = kwargs.get("hand_recommender") is not None
        super().__init__(observer, **kwargs)

        self.playstyle_profiler = BalatroBuildProfiler()
        self.playstyle_intent_tracker = BalatroPlaystyleIntentTracker()
        self.build_intent_log_tracker = BuildIntentLogTracker(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
        )

        joker_build_value = JokerBuildValueEvaluator(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
        )
        shared_item_estimator = DefaultShopItemValueEstimator(
            joker_build_value=joker_build_value,
        )
        self.shop_policy = VoucherAwareBalatroShopPolicy(
            item_value_estimator=shared_item_estimator,
        )
        self.shop_reroll_policy = BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )
        self.shop_arbiter = BuildAwareShopArbiter(
            shop_policy=self.shop_policy,
            reroll_policy=self.shop_reroll_policy,
        )
        self.pack_policy = BalatroPackPolicy(
            item_estimator=shared_item_estimator,
            playstyle_evaluator=PackPlaystyleEvaluator(
                profiler=self.playstyle_profiler,
                intent_tracker=self.playstyle_intent_tracker,
            ),
        )

        if not custom_hand_recommender:
            self.hand_recommender = self._recommend_hand_with_playstyle

    def decide(self) -> PlaystyleAutonomousStepDecision:
        decision = super().decide()
        return PlaystyleAutonomousStepDecision(
            snapshot=decision.snapshot,
            state=decision.state,
            action=decision.action,
            source=decision.source,
            notes=decision.notes,
            pack_signature=decision.pack_signature,
            build_intent=self.build_intent_log_tracker.prepare(decision.state),
        )

    def _hand_policy(
        self,
        thresholds: HandActionThresholds,
    ) -> BuildAwareLiveHandActionPolicy:
        return BuildAwareLiveHandActionPolicy(
            thresholds,
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
        )

    def _recommend_hand_with_playstyle(self, state, snapshot):
        del snapshot
        playbook = default_balatro_playbooks().for_state(state)
        thresholds = HandActionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get("hand_action", {})
        )
        planner_config = playbook.strategy.get("planner", {})
        max_horizon = (
            self.max_horizon
            if self.max_horizon is not None
            else int(planner_config.get("max_horizon", 8))
        )
        max_search_nodes = (
            self.max_search_nodes
            if self.max_search_nodes is not None
            else int(planner_config.get("max_search_nodes", 5000))
        )
        search_schedule_mode = _search_schedule_mode(
            planner_config,
            max_horizon_override=self.max_horizon,
            max_search_nodes_override=self.max_search_nodes,
        )
        engine = LiveHandActionDecisionEngine(
            policy=self._hand_policy(thresholds),
            max_horizon=max_horizon,
            max_search_nodes=max_search_nodes,
            exact_limit=self.exact_limit,
            child_exact_limit=self.child_exact_limit,
            search_schedule_mode=search_schedule_mode,
        )

        rank_timings: list[float] = []
        original_rank_plans = engine.rank_plans

        def timed_rank_plans(current_state, *, planner=None):
            started = perf_counter()
            try:
                return original_rank_plans(current_state, planner=planner)
            finally:
                rank_timings.append(perf_counter() - started)

        engine.rank_plans = timed_rank_plans
        decision_started = perf_counter()
        decision = engine.decide(state)
        d1_elapsed = perf_counter() - decision_started

        notes = [
            f"playbook={playbook.name} v{playbook.version}",
            f"search_schedule={search_schedule_mode}",
            f"mode={decision.mode}",
            f"confidence={decision.confidence:.6f}",
            f"indices={_indices(state, decision.action)}",
            (
                "clear_probability="
                f"{decision.selected_plan.value.clear_probability:.6f}"
            ),
            f"path_exact={decision.selected_plan.exact}",
            f"d1_decision_seconds={d1_elapsed:.3f}",
        ]
        if decision.selected_pace_ratio is not None:
            notes.append(f"pace_ratio={decision.selected_pace_ratio:.6f}")

        # Build-intent rationale belongs in the ordinary durable D1 decision notes.
        notes.extend(str(note) for note in decision.rationale if note.startswith("D1 "))

        for index, attempt in enumerate(decision.search_attempts):
            elapsed = rank_timings[index] if index < len(rank_timings) else float("nan")
            stage = "confirmation" if attempt.confirmation else "adaptive"
            best_action = attempt.best_action or "NONE"
            best_clear_probability = (
                f"{attempt.best_clear_probability:.6f}"
                if attempt.best_clear_probability is not None
                else "NONE"
            )
            best_expected_score = (
                f"{attempt.best_expected_score:.3f}"
                if attempt.best_expected_score is not None
                else "NONE"
            )
            best_exact = (
                str(attempt.best_exact) if attempt.best_exact is not None else "NONE"
            )
            notes.append(
                "search[{}]={} h={} samples={} nodes={}/{} budget_exceeded={} "
                "elapsed={:.3f}s best_action={} best_clear_probability={} "
                "best_expected_score={} best_exact={}".format(
                    index,
                    stage,
                    attempt.horizon,
                    attempt.samples,
                    attempt.nodes_evaluated,
                    attempt.max_nodes,
                    attempt.budget_exceeded,
                    elapsed,
                    best_action,
                    best_clear_probability,
                    best_expected_score,
                    best_exact,
                )
            )

        if len(rank_timings) > len(decision.search_attempts):
            fallback_elapsed = sum(rank_timings[len(decision.search_attempts):])
            notes.append(f"fallback_search_elapsed={fallback_elapsed:.3f}s")

        return decision.action, tuple(notes)
