from __future__ import annotations

from dataclasses import replace

from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.live.strategy_consumable_timing import (
    StrategyAwareLiveConsumableTimingPolicy,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.live.strategy_planet_policy import StrategyAwareLivePlanetPolicy
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.playbook_consumable_policy import PlaybookConsumableAcquisitionPolicy
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.playbook_shop_policy import PlaybookVoucherAwareBalatroShopPolicy
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.strategy_blind_skip_policy import StrategyAwareBlindSkipPolicy
from games.balatro.strategy_booster_policy import StrategyAwarePlaybookShopArbiter
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_compat import NeutralLegacyPlaystyleIntentTracker
from games.balatro.strategy_pack_playstyle import StrategyAwarePackPlaystyleEvaluator
from games.balatro.strategy_tree_catalog import (
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)
from games.balatro.strategy_value import (
    StrategyAwareConsumableSynergyEvaluator,
    StrategyAwareJokerBuildTransitionPlanner,
    StrategyAwareJokerBuildValueEvaluator,
)

from .playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)


def _strategy_modifiers_for_state(state):
    try:
        return default_balatro_playbooks().for_state(state).strategy_modifiers()
    except BalatroPlaybookNotFound:
        return {}


class StrategyAwareLiveMemoryInjectedSingleStepRunner(
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner
):
    """Production runner with run-scoped universal strategy scoring.

    The parent runner remains useful mechanics/plumbing, but its old playstyle
    intent is neutralized here. Universal playbooks are the only strategic source
    of truth in this production subclass.
    """

    def __init__(self, observer, **kwargs) -> None:
        custom_hand_recommender = kwargs.get("hand_recommender") is not None
        custom_pack_recommender = kwargs.get("pack_recommender") is not None
        super().__init__(observer, **kwargs)

        # The parent wires several mature policies to one legacy Ante-5-locking
        # playstyle tracker. Keep the mechanics but neutralize that strategic signal
        # before constructing the universal-strategy wrappers. Build-intent logging
        # retains the neutral bridge while strategy diagnostics below become the
        # authoritative strategic record.
        self.playstyle_intent_tracker = NeutralLegacyPlaystyleIntentTracker()
        self.build_intent_log_tracker.intent_tracker = self.playstyle_intent_tracker

        self.strategy_tracker = TreeAwareStateAwareBalatroStrategyTracker(
            RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
            topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
            modifier_provider=_strategy_modifiers_for_state,
        )
        self.blind_skip_policy = StrategyAwareBlindSkipPolicy(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
            strategy_tracker=self.strategy_tracker,
        )

        strategy_planet_policy = StrategyAwareLivePlanetPolicy(
            hand_evaluator=self.consumable_timing_policy.hand_evaluator,
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
            strategy_tracker=self.strategy_tracker,
        )
        self.consumable_timing_policy = StrategyAwareLiveConsumableTimingPolicy.from_policy(
            self.consumable_timing_policy,
            strategy_tracker=self.strategy_tracker,
            planet_policy=strategy_planet_policy,
        )

        joker_build_value = StrategyAwareJokerBuildValueEvaluator(
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
            strategy_tracker=self.strategy_tracker,
        )
        joker_transition_planner = StrategyAwareJokerBuildTransitionPlanner(
            evaluator=joker_build_value,
        )
        self.joker_order_policy = JokerOrderPolicy(evaluator=joker_build_value)
        consumable_build = StrategyAwareConsumableSynergyEvaluator(
            profiler=self.playstyle_profiler,
            strategy_tracker=self.strategy_tracker,
        )
        shared_item_estimator = BuildAwareShopItemValueEstimator(
            joker_build_value=joker_build_value,
            consumable_build=consumable_build,
        )

        self.shop_policy = PlaybookVoucherAwareBalatroShopPolicy(
            item_value_estimator=shared_item_estimator,
        )
        self.shop_reroll_policy = BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )
        self.shop_arbiter = StrategyAwarePlaybookShopArbiter(
            shop_policy=self.shop_policy,
            reroll_policy=self.shop_reroll_policy,
            joker_policy=PlaybookJokerAcquisitionPolicy(
                joker_transition_planner,
            ),
            consumable_policy=PlaybookConsumableAcquisitionPolicy(
                evaluator=consumable_build,
                timing_policy=self.consumable_timing_policy,
            ),
            strategy_tracker=self.strategy_tracker,
        )
        self.pack_policy = PlaybookBalatroPackPolicy(
            item_estimator=shared_item_estimator,
            playstyle_evaluator=StrategyAwarePackPlaystyleEvaluator(
                profiler=self.playstyle_profiler,
                intent_tracker=self.playstyle_intent_tracker,
                strategy_tracker=self.strategy_tracker,
            ),
        )

        if not custom_hand_recommender:
            self.hand_recommender = self._recommend_hand_with_playstyle
        if not custom_pack_recommender:
            self.pack_recommender = self._recommend_pack_with_diagnostics

    def _hand_policy(
        self,
        thresholds: HandActionThresholds,
    ) -> StrategyAwareLiveHandActionPolicy:
        return StrategyAwareLiveHandActionPolicy(
            thresholds,
            profiler=self.playstyle_profiler,
            intent_tracker=self.playstyle_intent_tracker,
            strategy_tracker=self.strategy_tracker,
        )

    def decide(self):
        decision = super().decide()
        order_decision = self.joker_order_policy.recommend(
            decision.state,
            phase=str(decision.snapshot.phase),
        )
        if order_decision is not None:
            decision = replace(
                decision,
                action=order_decision.to_action(),
                source="Joker-order policy",
                notes=order_decision.rationale,
                decision_diagnostics={
                    "layer": "JOKER_ORDER",
                    "selected": {
                        "permutation": list(order_decision.permutation),
                        "current_score": float(order_decision.current_score),
                        "ordered_score": float(order_decision.ordered_score),
                    },
                },
            )
        resolution = self.strategy_tracker.observe(decision.state)
        tree_nodes = self.strategy_tracker.tree_node_scores()
        diagnostics = dict(decision.decision_diagnostics or {})
        diagnostics["strategy"] = {
            "dominant_strategy_id": resolution.dominant_strategy_id,
            "relevant_strategy_ids": list(resolution.relevant_strategy_ids),
            # Compatibility names remain during the v1.0 migration.
            "active_strategy_id": resolution.active_strategy_id,
            "highlighted_strategy_id": resolution.highlighted_strategy_id,
            "committed_strategy_id": resolution.committed_strategy_id,
            "active_status": resolution.active_status,
            "strategy_pressure": float(
                self.strategy_tracker.strategy_pressure(decision.state)
            ),
            "legacy_playstyle_strategy_enabled": False,
            "changed": resolution.changed,
            # Actionable rankings contain the current specialization frontier.
            "ranked": [
                {
                    "strategy_id": assessment.strategy_id,
                    "name": assessment.name,
                    "score": float(assessment.score),
                    "base_score": float(assessment.base_score),
                    "effectiveness": float(assessment.effectiveness),
                    "status": assessment.status,
                    "gold_owned": int(assessment.gold_owned),
                    "silver_owned": int(assessment.silver_owned),
                    "bronze_owned": int(assessment.bronze_owned),
                    "banned_owned": int(assessment.banned_owned),
                }
                for assessment in resolution.assessments
            ],
            # Replaced and inactive nodes remain visible for diagnostics.
            "nodes": [
                {
                    "strategy_id": strategy_id,
                    "path": list(
                        self.strategy_tracker.topology.path(strategy_id)
                    ),
                    "is_leaf": bool(node.is_leaf),
                    "on_frontier": bool(node.on_frontier),
                    "active": bool(node.active),
                    "direct_evidence": float(node.direct_evidence),
                    "foundation_score": float(node.foundation_score),
                    "effective_score": float(node.effective_score),
                }
                for strategy_id, node in sorted(tree_nodes.items())
            ],
        }
        return replace(
            decision,
            notes=(*decision.notes, *resolution.rationale),
            decision_diagnostics=diagnostics,
        )
