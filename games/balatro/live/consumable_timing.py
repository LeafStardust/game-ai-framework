from __future__ import annotations

from dataclasses import replace

from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.live.consumable_timing_core import *  # noqa: F401,F403
from games.balatro.live.consumable_timing_core import (
    LiveConsumableTimingPolicy as _CoreLiveConsumableTimingPolicy,
)


class SteelAwareConsumableTargetEvaluator(ContextualConsumableTargetEvaluator):
    """Prefer cards that are cheap to keep in hand when creating Steel cards."""

    _RANK_COST = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 10,
        "Q": 10,
        "K": 10,
        "A": 11,
    }

    def rank_targets(self, state, consumable):
        ranked = super().rank_targets(state, consumable)
        if str(getattr(consumable, "name", "")) != "The Chariot":
            return ranked

        def hold_cost(evaluation):
            card = evaluation.cards[0]
            enhancement = str(getattr(card, "enhancement", "") or "")
            edition = str(getattr(card, "edition", "") or "")
            seal = str(getattr(card, "seal", "") or "")

            # Steel only pays while held. Do not consume cards that are already
            # valuable scoring pieces merely because Steel has a high generic
            # enhancement value. Blue Seal is intentionally exempt: it already
            # wants to remain in hand and therefore naturally pairs with Steel.
            scoring_enhancement_cost = 20.0 if enhancement else 0.0
            edition_cost = 12.0 if edition else 0.0
            permanent_chip_cost = max(
                0.0,
                float(getattr(card, "permanent_bonus", 0) or 0) / 5.0,
            )
            seal_cost = 0.0 if seal in {"", "Blue"} else 8.0
            rank_cost = float(self._RANK_COST.get(str(getattr(card, "rank", "")), 0))
            return (
                scoring_enhancement_cost
                + edition_cost
                + permanent_chip_cost
                + seal_cost
                + rank_cost
            )

        return tuple(
            sorted(
                ranked,
                key=lambda evaluation: (
                    hold_cost(evaluation),
                    -float(evaluation.total_gain),
                    evaluation.target_indices,
                ),
            )
        )


class LiveConsumableTimingPolicy(_CoreLiveConsumableTimingPolicy):
    """Held-consumable timing with an explicit D1 blind-clear handoff.

    B6 continues to own ordinary USE/HOLD timing. When a deterministic held
    consumable turns the current best visible play from non-guaranteed into a
    guaranteed immediate blind clear, the default runtime inventory view defers
    the entire SELECTING_HAND consumable arbitration to D1. D1 can request the
    undeferred recommendations and compare that consumable against Play/Discard
    in the normal blind planner.
    """

    def __init__(
        self,
        *,
        defer_blind_clear_to_d1: bool = True,
        **kwargs,
    ) -> None:
        kwargs.setdefault("target_evaluator", SteelAwareConsumableTargetEvaluator())
        super().__init__(**kwargs)
        self.defer_blind_clear_to_d1 = bool(defer_blind_clear_to_d1)

    def recommend(self, state, consumable: object) -> ConsumableTimingRecommendation:
        recommendation = super().recommend(state, consumable)

        # Wheel has no deterministic setup payoff from waiting for a smaller target
        # pool: its success probability is unchanged, and every eligible edition is
        # beneficial. The old policy held a positive-EV Wheel whenever >1 editionless
        # Joker existed, which caused chronic inventory hoarding. In SHOP, consume it
        # whenever the analytic evaluator reports positive expected build gain. Blind
        # checkpoints retain the ordinary D1/D5 timing hierarchy.
        if (
            getattr(state, "phase", None) == "SHOP"
            and str(getattr(consumable, "name", "")) == "The Wheel of Fortune"
            and not recommendation.should_use
            and float(recommendation.immediate_gain) > self.EPSILON
        ):
            return replace(
                recommendation,
                decision=USE,
                rationale=(
                    "USE: positive-EV Wheel should not be hoarded in SHOP solely because multiple editionless Jokers are eligible",
                    "Wheel success odds do not improve merely by waiting for a smaller eligible target pool",
                    *recommendation.rationale,
                ),
            )

        return recommendation

    def blind_clear_recommendations(
        self,
        state,
    ) -> tuple[ConsumableTimingRecommendation, ...]:
        """Return deterministic timing recommendations that prove a new clear."""
        recommendations = super().recommend_inventory(state)
        return tuple(
            recommendation
            for recommendation in recommendations
            if self._is_guaranteed_clear_upgrade(recommendation)
        )

    def recommend_inventory(
        self,
        state,
    ) -> tuple[ConsumableTimingRecommendation, ...]:
        recommendations = super().recommend_inventory(state)
        if (
            not self.defer_blind_clear_to_d1
            or getattr(state, "phase", None) != "SELECTING_HAND"
            or not any(
                self._is_guaranteed_clear_upgrade(recommendation)
                for recommendation in recommendations
            )
        ):
            return recommendations

        # A proven blind-clear path outranks non-clear timing such as economy or
        # slot-pressure use. Suppress every immediate B6 USE for this checkpoint
        # so the runtime falls through to D1, which will compare the clear-enabling
        # consumable with ordinary Play/Discard and execute only its first action.
        deferred = tuple(
            replace(
                recommendation,
                decision=HOLD,
                rationale=(
                    "HOLD: guaranteed blind-clear consumable arbitration is delegated to D1",
                    *recommendation.rationale,
                ),
            )
            if recommendation.should_use
            else recommendation
            for recommendation in recommendations
        )
        return tuple(
            sorted(
                deferred,
                key=self._recommendation_key,
                reverse=True,
            )
        )

    @staticmethod
    def _is_guaranteed_clear_upgrade(
        recommendation: ConsumableTimingRecommendation,
    ) -> bool:
        before = recommendation.before_projection
        after = recommendation.after_projection
        return bool(
            recommendation.should_use
            and before is not None
            and after is not None
            and before.joker_projection_complete
            and after.joker_projection_complete
            and not before.clears_blind
            and after.clears_blind
        )
