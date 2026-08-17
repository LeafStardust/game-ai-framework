from __future__ import annotations

from dataclasses import replace

from games.balatro.shop_booster_policy import (
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
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
            if self.strategy_tracker.definitions[assessment.strategy_id].primary_hands
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
