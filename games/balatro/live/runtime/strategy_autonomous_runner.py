from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import SELECT_BLIND
from games.balatro.collection_mode import (
    CollectionFirstPackPolicy,
    CollectionFirstPolicy,
)
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.live.blind_clear_planner import (
    LiveBlindPlan,
    PlannerSearchBudgetExceeded,
)
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.joker_sale_policy import JokerSalePolicy
from games.balatro.live.riff_raff_cycle import RiffRaffCyclePolicy
from games.balatro.live.strategy_consumable_timing import (
    StrategyAwareLiveConsumableTimingPolicy,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.live.strategy_planet_policy import StrategyAwareLivePlanetPolicy
from games.balatro.live.pack import LivePackActionGenerator
from games.balatro.live.verdant_leaf import VerdantLeafSalePolicy
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.playbook_consumable_policy import PlaybookConsumableAcquisitionPolicy
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.playbook_shop_policy import PlaybookVoucherAwareBalatroShopPolicy
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.strategy_blind_skip_policy import StrategyAwareBlindSkipPolicy
from games.balatro.strategy_booster_policy import (
    StrategyAwarePlaybookShopArbiter,
    StrategyAwareShopRerollPolicy,
)
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
from games.balatro.unlock_campaign import (
    AUTO,
    UnlockCampaignConfig,
    UnlockCampaignPolicy,
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
        unlock_campaign_config = kwargs.pop("unlock_campaign_config", None)
        self.collection_first = bool(kwargs.pop("collection_first", False))
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
        self.verdant_leaf_sale_policy = VerdantLeafSalePolicy(
            evaluator=joker_build_value,
        )
        self.riff_raff_cycle_policy = RiffRaffCyclePolicy(
            evaluator=joker_build_value,
        )
        self.hand_order_policy = HandOrderPolicy()
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
        effective_unlock_config = unlock_campaign_config or UnlockCampaignConfig()
        if self.collection_first and not effective_unlock_config.enabled:
            effective_unlock_config = UnlockCampaignConfig.from_targets((AUTO,))
        self.unlock_campaign_policy = UnlockCampaignPolicy(
            effective_unlock_config,
            preserve_clear_probability=not self.collection_first,
        )
        self.collection_policy = CollectionFirstPolicy(
            joker_sale_policy=JokerSalePolicy(evaluator=joker_build_value),
            item_estimator=shared_item_estimator,
        )

        self.shop_policy = PlaybookVoucherAwareBalatroShopPolicy(
            item_value_estimator=shared_item_estimator,
        )
        self.shop_reroll_policy = StrategyAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
            strategy_tracker=self.strategy_tracker,
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
        if self.collection_first:
            self.pack_generator = LivePackActionGenerator(
                include_capacity_blocked_jokers=True,
            )
            self.pack_policy = CollectionFirstPackPolicy(
                self.pack_policy,
                collection_policy=self.collection_policy,
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
        collection = (
            self.collection_policy.recommend_shop(decision.state)
            if self.collection_first
            else None
        )
        if collection is not None:
            decision = replace(
                decision,
                action=collection.action,
                source=f"Collection-first: {collection.priority}",
                notes=collection.rationale,
                decision_diagnostics={
                    "layer": collection.priority,
                    "selected": {
                        "target_kind": collection.target_kind,
                        "target_label": collection.target_label,
                        "action": str(collection.action.name),
                    },
                },
            )
            unlock = None
        else:
            unlock = self._unlock_campaign_recommendation(decision)
        if collection is None and unlock is not None:
            decision = replace(
                decision,
                action=unlock.action,
                source=f"Joker unlock campaign: {unlock.target_label}",
                notes=unlock.rationale,
                decision_diagnostics={
                    "layer": "JOKER_UNLOCK_CAMPAIGN",
                    "selected": {
                        "target_id": unlock.target_id,
                        "target_label": unlock.target_label,
                        "action": str(unlock.action.name),
                    },
                },
            )
        elif collection is None:
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
            retention_diagnostics = tuple(
                self.joker_order_policy.last_negative_retention_diagnostics
            )
            if retention_diagnostics:
                diagnostics = dict(decision.decision_diagnostics or {})
                diagnostics["negative_retention"] = {
                    "source": "JOKER_ORDER",
                    "rationale": list(retention_diagnostics),
                }
                decision = replace(
                    decision,
                    notes=(
                        decision.notes
                        if order_decision is not None
                        else (*decision.notes, *retention_diagnostics)
                    ),
                    decision_diagnostics=diagnostics,
                )
        if str(decision.source) == "D1 hand-action policy":
            engine = self.last_hand_action_engine
            evaluator = engine.planner.evaluator if engine is not None else None
            hand_order = self.hand_order_policy.recommend(
                decision.state,
                decision.action,
                evaluator=evaluator,
            )
            if hand_order is not None:
                decision = replace(
                    decision,
                    action=hand_order.to_action(),
                    source="Hand-order policy",
                    notes=hand_order.rationale,
                    decision_diagnostics={
                        "layer": "HAND_ORDER",
                        "selected": {
                            "permutation": list(hand_order.permutation),
                            "current_guaranteed_score": int(
                                hand_order.current_guaranteed_score
                            ),
                            "ordered_guaranteed_score": int(
                                hand_order.ordered_guaranteed_score
                            ),
                            "current_expected_score": float(
                                hand_order.current_expected_score
                            ),
                            "ordered_expected_score": float(
                                hand_order.ordered_expected_score
                            ),
                        },
                    },
                )

        riff_raff_sale = self.riff_raff_cycle_policy.recommend(
            decision.state,
            will_select_blind=(
                str(decision.snapshot.phase) == "BLIND_SELECT"
                and str(decision.action.name) == SELECT_BLIND
            ),
        )
        if riff_raff_sale is not None:
            decision = replace(
                decision,
                action=riff_raff_sale.to_action(),
                source="Riff-Raff pre-round cycle policy",
                notes=riff_raff_sale.rationale,
                decision_diagnostics={
                    "layer": "RIFF_RAFF_CYCLE",
                    "selected": {
                        "joker_index": int(riff_raff_sale.joker_index),
                        "joker": riff_raff_sale.joker,
                        "retention_cost": float(riff_raff_sale.retention_cost),
                        "free_slots_before": int(riff_raff_sale.free_slots_before),
                    },
                },
            )

        verdant_sale = self.verdant_leaf_sale_policy.recommend(decision.state)
        if verdant_sale is not None:
            decision = replace(
                decision,
                action=verdant_sale.to_action(),
                source="Verdant Leaf emergency sale policy",
                notes=verdant_sale.rationale,
                decision_diagnostics={
                    "layer": "BOSS_VERDANT_LEAF",
                    "selected": {
                        "joker_index": int(verdant_sale.joker_index),
                        "joker": verdant_sale.joker,
                        "retention_cost": float(verdant_sale.retention_cost),
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

    def _unlock_campaign_recommendation(self, decision):
        state = decision.state
        if str(decision.snapshot.phase) != "SELECTING_HAND":
            return None
        if str(decision.source) != "D1 hand-action policy":
            return None
        if not self.unlock_campaign_policy.active_targets(state):
            return None

        hand_decision = self.last_hand_action_decision
        engine = self.last_hand_action_engine
        if hand_decision is None or engine is None:
            return None

        depth = max(1, int(getattr(hand_decision.selected_plan, "horizon", 1)))
        planner = engine.planner

        def evaluate_forced_action(action):
            try:
                planner._require_state(state)
                planner.reset_search_stats()
                estimate = planner._estimate_action(state, action, depth)
            except (PlannerSearchBudgetExceeded, RuntimeError, ValueError):
                return None
            return LiveBlindPlan(
                action=action,
                value=estimate.value,
                horizon=depth,
                exact=estimate.exact,
                candidate_count=1,
            )

        baseline = evaluate_forced_action(hand_decision.action)
        if baseline is None:
            return None

        evaluator = planner.evaluator
        play_actions = tuple(
            plan.action
            for plan in getattr(hand_decision, "plans", ())
            if str(plan.action.name) == "PLAY_CARDS"
        )
        if not play_actions and str(hand_decision.action.name) == "PLAY_CARDS":
            play_actions = (hand_decision.action,)
        return self.unlock_campaign_policy.recommend_hand(
            state,
            baseline_plan=baseline,
            evaluate_forced_action=evaluate_forced_action,
            play_actions=play_actions,
            project_play=lambda action: evaluator.project_play(state, action),
        )
