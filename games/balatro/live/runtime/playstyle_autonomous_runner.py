from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from games.balatro.build.joker_strategy import (
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
)
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
)
from games.balatro.live.build_intent_log import (
    BuildIntentLogTracker,
    PreparedBuildIntentLog,
)
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine as LiveHandActionDecisionEngine,
)
from games.balatro.live.hand_playstyle import BuildAwareLiveHandActionPolicy
from games.balatro.live.planet_policy import LivePlanetPolicy
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy

from .live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
    _indices,
    _pack_choice_signature,
    _search_schedule_mode,
)


@dataclass(frozen=True)
class PlaystyleAutonomousStepDecision(AutonomousStepDecision):
    build_intent: PreparedBuildIntentLog | None = None
    decision_diagnostics: dict[str, Any] | None = None


class PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
    LiveMemoryInjectedSingleStepRunner
):
    """Production single-step runner with one run-scoped build-intent lifecycle.

    The base runner remains the mechanics/execution implementation. This adapter
    wires one competence-layer playstyle tracker into D1 hand decisions, D2
    Joker/shop valuation, D7 Planet choices, D9 booster choices, D14 cross-category
    shop valuation, structured run logging, and the dedicated D3 persistent-voucher
    shop policy. A supervisor retry creates a fresh runner and therefore a fresh
    playstyle tracker.
    """

    def __init__(self, observer, **kwargs) -> None:
        custom_hand_recommender = kwargs.get("hand_recommender") is not None
        custom_pack_recommender = kwargs.get("pack_recommender") is not None
        custom_consumable_timing_policy = (
            kwargs.get("consumable_timing_policy") is not None
        )
        super().__init__(observer, **kwargs)

        self.playstyle_profiler = BalatroBuildProfiler()
        self.playstyle_intent_tracker = BalatroPlaystyleIntentTracker()
        self.build_intent_log_tracker = BuildIntentLogTracker(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
        )

        if not custom_consumable_timing_policy:
            self.consumable_timing_policy.planet_policy = LivePlanetPolicy(
                hand_evaluator=self.consumable_timing_policy.hand_evaluator,
                profiler=self.playstyle_profiler,
                intent_tracker=self.playstyle_intent_tracker,
            )

        joker_build_value = JokerBuildValueEvaluator(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
        )
        joker_transition_planner = JokerBuildTransitionPlanner(
            evaluator=joker_build_value,
        )
        shared_item_estimator = BuildAwareShopItemValueEstimator(
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
            joker_policy=PlaybookJokerAcquisitionPolicy(
                joker_transition_planner,
            ),
        )
        self.pack_policy = BalatroPackPolicy(
            item_estimator=shared_item_estimator,
            playstyle_evaluator=PackPlaystyleEvaluator(
                profiler=self.playstyle_profiler,
                intent_tracker=self.playstyle_intent_tracker,
            ),
        )
        self._pending_decision_diagnostics: dict[str, Any] = {}

        if not custom_hand_recommender:
            self.hand_recommender = self._recommend_hand_with_playstyle
        if not custom_pack_recommender:
            self.pack_recommender = self._recommend_pack_with_diagnostics

    def decide(self) -> PlaystyleAutonomousStepDecision:
        self._pending_decision_diagnostics = {}
        decision = super().decide()
        playbook = default_balatro_playbooks().for_state(decision.state)
        diagnostics = dict(self._pending_decision_diagnostics)
        diagnostics.setdefault("decision_source", str(decision.source))
        diagnostics.setdefault(
            "active_thresholds",
            playbook.strategy.get("decision_thresholds", {}),
        )
        return PlaystyleAutonomousStepDecision(
            snapshot=decision.snapshot,
            state=decision.state,
            action=decision.action,
            source=decision.source,
            notes=decision.notes,
            pack_signature=decision.pack_signature,
            build_intent=self.build_intent_log_tracker.prepare(decision.state),
            decision_diagnostics=diagnostics,
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

    def _recommend_pack_with_diagnostics(self, state, snapshot):
        del snapshot
        choices = tuple(self.pack_choice_reader())
        actions = self.pack_generator.generate_actions(state, list(choices))
        ranked = self.pack_policy.rank_actions(state, actions)
        if not ranked:
            raise RuntimeError("pack policy produced no scoreable action")

        candidates = []
        for result in ranked:
            target = getattr(result.action, "target", None)
            candidates.append(
                {
                    "action": str(result.action.name),
                    "score": float(result.total),
                    "area_index": getattr(target, "area_index", None),
                    "label": getattr(target, "label", None),
                    "notes": [str(note) for note in result.notes],
                }
            )
        self._pending_decision_diagnostics = {
            "layer": "D9/D10",
            "candidate_scores": candidates,
            "active_thresholds": {"pack_skip_bias": float(self.pack_policy.skip_bias)},
        }

        selected = ranked[0]
        notes = [f"policy_score={selected.total:.6f}"]
        notes.extend(str(note) for note in selected.notes)
        return selected.action, tuple(notes), _pack_choice_signature(choices)

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

        notes.extend(str(note) for note in decision.rationale if note.startswith("D1 "))

        search_diagnostics = []
        for index, attempt in enumerate(decision.search_attempts):
            elapsed = rank_timings[index] if index < len(rank_timings) else float("nan")
            best_action = attempt.best_action or "NONE"
            search_diagnostics.append(
                {
                    "stage": "confirmation" if attempt.confirmation else "adaptive",
                    "horizon": int(attempt.horizon),
                    "samples": int(attempt.samples),
                    "nodes_evaluated": int(attempt.nodes_evaluated),
                    "max_nodes": int(attempt.max_nodes),
                    "budget_exceeded": bool(attempt.budget_exceeded),
                    "best_action": best_action,
                    "best_clear_probability": attempt.best_clear_probability,
                    "best_expected_score": attempt.best_expected_score,
                    "best_exact": attempt.best_exact,
                    "elapsed_seconds": float(elapsed),
                }
            )
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
                    "confirmation" if attempt.confirmation else "adaptive",
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

        self._pending_decision_diagnostics = {
            "layer": "D1",
            "active_thresholds": playbook.strategy.get("decision_thresholds", {}).get(
                "hand_action", {}
            ),
            "selected": {
                "action": str(decision.action.name),
                "confidence": float(decision.confidence),
                "clear_probability": float(decision.selected_plan.value.clear_probability),
                "expected_score": float(decision.selected_plan.value.expected_score),
                "exact": bool(decision.selected_plan.exact),
                "pace_ratio": decision.selected_pace_ratio,
            },
            "search_attempts": search_diagnostics,
        }

        if len(rank_timings) > len(decision.search_attempts):
            fallback_elapsed = sum(rank_timings[len(decision.search_attempts):])
            notes.append(f"fallback_search_elapsed={fallback_elapsed:.3f}s")

        return decision.action, tuple(notes)
