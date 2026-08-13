from __future__ import annotations

from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.live.consumable_timing_base import *  # noqa: F401,F403
from games.balatro.live.consumable_timing_base import (
    LiveConsumableTimingPolicy as _BaseLiveConsumableTimingPolicy,
)


class LiveConsumableTimingPolicy(_BaseLiveConsumableTimingPolicy):
    """B6 held-consumable timing with analytic Wheel of Fortune support.

    The green deterministic/targeted timing implementation remains in
    ``consumable_timing_base``. Wheel adds one stochastic-but-analytic path that
    consumes only public state and never samples Balatro RNG or reads its seed.
    """

    def __init__(self, *, wheel_evaluator=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.wheel_evaluator = wheel_evaluator or WheelOfFortuneExpectationEvaluator()

    def recommend(self, state, consumable: object) -> ConsumableTimingRecommendation:
        name = str(getattr(consumable, "name", ""))
        if name != "The Wheel of Fortune":
            return super().recommend(state, consumable)

        if getattr(state, "phase", None) != "SELECTING_HAND":
            return self._hold(
                state,
                consumable,
                "consumable timing requires SELECTING_HAND",
            )
        if self._identity_index(getattr(state, "consumables", ()), consumable) is None:
            return self._hold(state, consumable, "candidate consumable is not held")
        return self._recommend_wheel(state, consumable)

    def _recommend_wheel(
        self,
        state,
        consumable: object,
    ) -> ConsumableTimingRecommendation:
        expectation = self.wheel_evaluator.evaluate(state)

        if not expectation.available:
            return self._hold(
                state,
                consumable,
                "Wheel has no editionless public Joker target",
            )
        if not expectation.complete:
            return self._hold(
                state,
                consumable,
                "Wheel stochastic expectation is incomplete",
            )

        expected_gain = float(expectation.expected_build_gain)
        if expected_gain <= self.EPSILON:
            return self._hold(
                state,
                consumable,
                "Wheel has no positive modeled expected build gain",
                immediate_gain=expected_gain,
            )

        slots_full = self._consumable_slots_full(state)
        eligible_count = len(expectation.eligible_indices)
        success_probability = float(expectation.success_probability)

        if eligible_count == 1:
            reason = (
                "exactly one editionless Joker is eligible, so a successful "
                "Wheel cannot dilute onto another target"
            )
            decision = USE
        elif success_probability >= 1.0 - self.EPSILON:
            reason = (
                "public probability modifiers make Wheel success effectively "
                "guaranteed"
            )
            decision = USE
        elif slots_full:
            reason = (
                "consumable slots are full and Wheel has positive analytic "
                "expected build gain"
            )
            decision = USE
        else:
            reason = (
                "multiple editionless Jokers remain eligible; preserve Wheel "
                "for a less diluted target set, better public odds, or slot pressure"
            )
            decision = HOLD

        return ConsumableTimingRecommendation(
            decision=decision,
            consumable=consumable,
            target=None,
            before_projection=None,
            after_projection=None,
            required_per_hand=self._required_per_hand(state),
            immediate_gain=expected_gain,
            rationale=(
                f"{decision}: {reason}",
                "Wheel uses analytic public-state expectation; no RNG sample or seed read",
                *expectation.rationale,
                f"consumable slots full={slots_full}",
            ),
        )
