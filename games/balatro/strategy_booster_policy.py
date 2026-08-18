from __future__ import annotations

from dataclasses import replace

from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.playbook_shop_policy import PlaybookBuildAwareShopArbiter
from games.balatro.shop_booster_policy import (
    HOLD,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollThresholds,
)
from games.balatro.strategy import BalatroStrategyTracker


class StrategyAwareShopBoosterPolicy(BuildAwareShopBoosterPolicy):
    """D8 booster policy driven by the universal playbook strategy state.

    Arcana and Spectral packs are safe to open because D9/D10 still inspect the
    visible post-open choices and may Skip. Celestial packs are different: Planets
    reinforce an existing poker-hand direction, so D8 requires meaningful current
    poker-hand evidence before spending on the unopened pack.
    """

    AUTONOMOUS_SAFE_FAMILIES = frozenset(
        {*BuildAwareShopBoosterPolicy.AUTONOMOUS_SAFE_FAMILIES, "ARCANA", "SPECTRAL"}
    )

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _primary_hands(self, strategy_id: str) -> tuple[str, ...]:
        getter = getattr(self.strategy_tracker, "primary_hands_for", None)
        if callable(getter):
            return tuple(getter(strategy_id))
        definition = self.strategy_tracker.definitions.get(strategy_id)
        return () if definition is None else tuple(definition.primary_hands)

    def recommend(self, state, action) -> ShopBoosterRecommendation:
        recommendation = super().recommend(state, action)
        if recommendation.family != "CELESTIAL":
            return recommendation

        config = self.strategy_tracker._config(state)
        evidence_floor = self.strategy_tracker._number(
            config,
            "celestial_poker_evidence_floor",
            1.5,
        )
        resolution = self.strategy_tracker.observe(state)
        poker_assessments = [
            assessment
            for assessment in resolution.assessments
            if self._primary_hands(assessment.strategy_id)
        ]
        best = max(poker_assessments, key=lambda item: item.score, default=None)
        best_score = float(best.score) if best is not None else 0.0
        best_name = best.name if best is not None else "none"

        if best_score < evidence_floor:
            return replace(
                recommendation,
                decision=HOLD,
                rationale=(
                    *recommendation.rationale,
                    f"Celestial blocked: best poker-hand strategy={best_name} score={best_score:.3f}",
                    f"Celestial poker-strategy evidence floor={evidence_floor:.3f}",
                    "Planets reinforce an evidenced poker-hand route; they do not seed one",
                ),
            )

        return replace(
            recommendation,
            rationale=(
                *recommendation.rationale,
                f"Celestial admitted by poker-hand strategy={best_name} score={best_score:.3f}",
                f"Celestial poker-strategy evidence floor={evidence_floor:.3f}",
            ),
        )


class StrategyAwareShopRerollPolicy(BuildAwareShopRerollPolicy):
    """Apply a larger paid-reroll reserve to Gold economy routes."""

    GOLD_ECONOMY_ROOTS = frozenset({"gold_cards", "gold_seal"})
    GOLD_EARLY_RESERVE = 25
    GOLD_LATE_RESERVE = 40
    GOLD_MAXIMUM_PAID_REROLL_COST = 6

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _is_gold_economy_route(self, strategy_id: str | None) -> bool:
        if strategy_id is None:
            return False
        path = (str(strategy_id),)
        topology = getattr(self.strategy_tracker, "topology", None)
        if topology is not None and strategy_id in topology.nodes:
            path = topology.path(strategy_id)
        return bool(self.GOLD_ECONOMY_ROOTS.intersection(path))

    def thresholds_for_state(self, state) -> ShopRerollThresholds:
        thresholds = super().thresholds_for_state(state)
        resolution = self.strategy_tracker.observe(state)
        if not self._is_gold_economy_route(resolution.dominant_strategy_id):
            return thresholds
        return replace(
            thresholds,
            maximum_paid_reroll_cost=min(
                int(thresholds.maximum_paid_reroll_cost),
                self.GOLD_MAXIMUM_PAID_REROLL_COST,
            ),
            minimum_money_after_paid_reroll=max(
                int(thresholds.minimum_money_after_paid_reroll),
                self.GOLD_EARLY_RESERVE,
            ),
            late_ante_minimum_money_after_paid_reroll=max(
                int(thresholds.late_ante_minimum_money_after_paid_reroll),
                self.GOLD_LATE_RESERVE,
            ),
        )


class StrategyAwarePlaybookShopArbiter(PlaybookBuildAwareShopArbiter):
    """Resolve D8 from the active cartridge while sharing universal strategy state."""

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _booster_policy_for_state(self, state) -> BuildAwareShopBoosterPolicy:
        if self.booster_policy is not None:
            return self.booster_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return StrategyAwareShopBoosterPolicy(
                shop_policy=self.shop_policy,
                strategy_tracker=self.strategy_tracker,
            )

        thresholds = BoosterAcquisitionThresholds.from_mapping(
            playbook.thresholds_for("D8")
        )
        return StrategyAwareShopBoosterPolicy(
            thresholds=thresholds,
            shop_policy=self.shop_policy,
            strategy_tracker=self.strategy_tracker,
        )
