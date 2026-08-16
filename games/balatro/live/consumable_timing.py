from __future__ import annotations

from dataclasses import replace

from games.balatro.live.consumable_timing_core import *  # noqa: F401,F403
from games.balatro.live.consumable_timing_core import (
    LiveConsumableTimingPolicy as _CoreLiveConsumableTimingPolicy,
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
        super().__init__(**kwargs)
        self.defer_blind_clear_to_d1 = bool(defer_blind_clear_to_d1)

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
