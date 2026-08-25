from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS, SELECT_BLIND
from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.collection_mode import CollectionFirstPackPolicy, CollectionFirstPolicy
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.joker_sale_policy import JokerSalePolicy
from games.balatro.live.blind_clear_planner import LiveBlindPlan, PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.live.riff_raff_cycle import RiffRaffCyclePolicy
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.live.verdant_leaf import VerdantLeafSalePolicy
from games.balatro.live.pack import LivePackActionGenerator
from games.balatro.unlock_campaign import AUTO, UnlockCampaignConfig, UnlockCampaignPolicy

from .bond_autonomous_runner import BondAwareLiveMemoryInjectedSingleStepRunner


class StrategyAwareLiveMemoryInjectedSingleStepRunner(
    BondAwareLiveMemoryInjectedSingleStepRunner
):
    """Production runner using canonical Bonds/composition for strategic direction.

    The historical categorical strategy tracker is intentionally absent. Mature
    mechanics from the parent runner remain, while Bond health, pivot authority,
    prescriptions, and D1 Bond hand shaping provide the current strategy layer.
    """

    def __init__(self, observer, **kwargs) -> None:
        unlock_campaign_config = kwargs.pop("unlock_campaign_config", None)
        self.collection_first = bool(kwargs.pop("collection_first", False))
        custom_hand_recommender = kwargs.get("hand_recommender") is not None
        custom_pack_recommender = kwargs.get("pack_recommender") is not None
        super().__init__(observer, **kwargs)

        joker_build_value = JokerBuildValueEvaluator()
        self.verdant_leaf_sale_policy = VerdantLeafSalePolicy(evaluator=joker_build_value)
        self.riff_raff_cycle_policy = RiffRaffCyclePolicy(evaluator=joker_build_value)
        self.hand_order_policy = HandOrderPolicy()
        self.joker_order_policy = JokerOrderPolicy(evaluator=joker_build_value)

        effective_unlock_config = unlock_campaign_config or UnlockCampaignConfig()
        if self.collection_first and not effective_unlock_config.enabled:
            effective_unlock_config = UnlockCampaignConfig.from_targets((AUTO,))
        self.unlock_campaign_policy = UnlockCampaignPolicy(
            effective_unlock_config,
            preserve_clear_probability=not self.collection_first,
        )
        self.collection_policy = CollectionFirstPolicy(
            joker_sale_policy=JokerSalePolicy(evaluator=joker_build_value),
            item_estimator=self.shop_policy.item_value_estimator,
        )
        if self.collection_first:
            self.pack_generator = LivePackActionGenerator(include_capacity_blocked_jokers=True)
            self.pack_policy = CollectionFirstPackPolicy(
                self.pack_policy,
                collection_policy=self.collection_policy,
            )

        if not custom_hand_recommender:
            self.hand_recommender = self._recommend_hand_with_bonds
        if not custom_pack_recommender:
            self.pack_recommender = self._recommend_pack_with_diagnostics

    def _hand_policy(self, thresholds: HandActionThresholds) -> StrategyAwareLiveHandActionPolicy:
        return StrategyAwareLiveHandActionPolicy(
            thresholds,
            profiler=self.build_profiler,
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
            retention_diagnostics = tuple(self.joker_order_policy.last_negative_retention_diagnostics)
            if retention_diagnostics:
                diagnostics = dict(decision.decision_diagnostics or {})
                diagnostics["negative_retention"] = {
                    "source": "JOKER_ORDER",
                    "rationale": list(retention_diagnostics),
                }
                decision = replace(
                    decision,
                    notes=(decision.notes if order_decision is not None else (*decision.notes, *retention_diagnostics)),
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
                            "current_guaranteed_score": int(hand_order.current_guaranteed_score),
                            "ordered_guaranteed_score": int(hand_order.ordered_guaranteed_score),
                            "current_expected_score": float(hand_order.current_expected_score),
                            "ordered_expected_score": float(hand_order.ordered_expected_score),
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

        diagnostics = dict(decision.decision_diagnostics or {})
        try:
            diagnostics["bond_strategy"] = bond_strategy_diagnostics(decision.state)
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        return replace(decision, decision_diagnostics=diagnostics)

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
            if str(plan.action.name) == PLAY_CARDS
        )
        if not play_actions and str(hand_decision.action.name) == PLAY_CARDS:
            play_actions = (hand_decision.action,)
        return self.unlock_campaign_policy.recommend_hand(
            state,
            baseline_plan=baseline,
            evaluate_forced_action=evaluate_forced_action,
            play_actions=play_actions,
            project_play=lambda action: evaluator.project_play(state, action),
        )
