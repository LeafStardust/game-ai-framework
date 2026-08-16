from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Mapping

from games.balatro.build.wheel_expectation import WheelOfFortuneExpectationEvaluator
from games.balatro.live.consumable_timing_base import *  # noqa: F401,F403
from games.balatro.live.consumable_timing_base import (
    LiveConsumableTimingPolicy as _BaseLiveConsumableTimingPolicy,
)
from games.balatro.live.planet_policy import LivePlanetPolicy
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks


@dataclass(frozen=True)
class ConsumableUseThresholds:
    """Thresholds owned only by D5 held-consumable USE/HOLD decisions."""

    minimum_clear_probability_gain: float = 0.0
    minimum_pace_score_gain: float = 0.0
    minimum_full_slot_contextual_delta: float = 0.0
    minimum_final_hand_score_gain: float = 0.0
    minimum_immediate_gain: float = 0.0

    def __post_init__(self) -> None:
        for field in fields(self):
            if float(getattr(self, field.name)) < 0.0:
                raise ValueError(f"{field.name} cannot be negative")

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "ConsumableUseThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D5 consumable-use threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})


@dataclass(frozen=True)
class ConsumableTargetThresholds:
    """Thresholds owned only by D6 deterministic consumable target admission."""

    minimum_total_gain: float | None = None
    minimum_contextual_delta: float | None = None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "ConsumableTargetThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D6 consumable-target threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def accepts(self, evaluation) -> bool:
        if (
            self.minimum_total_gain is not None
            and float(evaluation.total_gain) + 1e-12 < float(self.minimum_total_gain)
        ):
            return False
        if (
            self.minimum_contextual_delta is not None
            and float(evaluation.contextual_delta) + 1e-12
            < float(self.minimum_contextual_delta)
        ):
            return False
        return True


class LiveConsumableTimingPolicy(_BaseLiveConsumableTimingPolicy):
    """B6/D7 held-consumable timing with per-layer playbook thresholds.

    D5 owns USE/HOLD admission and D6 owns deterministic target admission. Their
    Red/White defaults reproduce the existing conservative behavior. D7 Planets
    retain their dedicated threshold contract. Wheel uses analytic public-state
    expectation only; no RNG sample or seed is consulted.
    """

    SHOP_SAFE_NO_TARGET_NAMES = frozenset(
        {"The Hermit", "Temperance", "The Wheel of Fortune"}
    )

    def __init__(
        self,
        *,
        wheel_evaluator=None,
        planet_policy=None,
        use_thresholds: ConsumableUseThresholds | None = None,
        target_thresholds: ConsumableTargetThresholds | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.wheel_evaluator = wheel_evaluator or WheelOfFortuneExpectationEvaluator()
        self.planet_policy = planet_policy or LivePlanetPolicy(
            hand_evaluator=self.hand_evaluator
        )
        self.use_thresholds = use_thresholds
        self.target_thresholds = target_thresholds

    def _use_thresholds_for_state(self, state) -> ConsumableUseThresholds:
        if self.use_thresholds is not None:
            return self.use_thresholds
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D5")
        except BalatroPlaybookNotFound:
            block = {}
        return ConsumableUseThresholds.from_mapping(block)

    def _target_thresholds_for_state(self, state) -> ConsumableTargetThresholds:
        if self.target_thresholds is not None:
            return self.target_thresholds
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D6")
        except BalatroPlaybookNotFound:
            block = {}
        return ConsumableTargetThresholds.from_mapping(block)

    def recommend(self, state, consumable: object) -> ConsumableTimingRecommendation:
        name = str(getattr(consumable, "name", ""))
        category = str(getattr(consumable, "category", "")).upper()
        phase = getattr(state, "phase", None)

        if category == "PLANET":
            return self._recommend_planet_d7(state, consumable)

        if phase == "SHOP":
            if self._identity_index(getattr(state, "consumables", ()), consumable) is None:
                return self._hold(state, consumable, "candidate consumable is not held")
            if name not in self.SHOP_SAFE_NO_TARGET_NAMES:
                return self._hold(
                    state,
                    consumable,
                    "SHOP timing admits only validated no-hand-target held consumables",
                )
            if name == "The Wheel of Fortune":
                recommendation = self._recommend_wheel(state, consumable)
            else:
                recommendation = self._recommend_economy(state, consumable, name=name)
            return self._apply_d5_d6_thresholds(state, recommendation)

        if name != "The Wheel of Fortune":
            recommendation = super().recommend(state, consumable)
            return self._apply_d5_d6_thresholds(state, recommendation)

        if phase != "SELECTING_HAND":
            return self._hold(
                state,
                consumable,
                "consumable timing requires SELECTING_HAND or validated SHOP use",
            )
        if self._identity_index(getattr(state, "consumables", ()), consumable) is None:
            return self._hold(state, consumable, "candidate consumable is not held")
        recommendation = self._recommend_wheel(state, consumable)
        return self._apply_d5_d6_thresholds(state, recommendation)

    def _apply_d5_d6_thresholds(
        self,
        state,
        recommendation: ConsumableTimingRecommendation,
    ) -> ConsumableTimingRecommendation:
        if not recommendation.should_use:
            return recommendation

        use_thresholds = self._use_thresholds_for_state(state)
        if (
            float(recommendation.immediate_gain) > self.EPSILON
            and float(recommendation.immediate_gain) + self.EPSILON
            < float(use_thresholds.minimum_immediate_gain)
        ):
            return replace(
                recommendation,
                decision=HOLD,
                rationale=(
                    "HOLD: D5 immediate-gain threshold blocks current use",
                    f"immediate_gain={recommendation.immediate_gain:.6f}",
                    f"minimum_immediate_gain={use_thresholds.minimum_immediate_gain:.6f}",
                    *recommendation.rationale,
                ),
            )

        if recommendation.target is not None:
            target_thresholds = self._target_thresholds_for_state(state)
            if not target_thresholds.accepts(recommendation.target):
                return replace(
                    recommendation,
                    decision=HOLD,
                    rationale=(
                        "HOLD: D6 target-admission threshold blocks current target",
                        f"target_total_gain={recommendation.target.total_gain:.6f}",
                        f"target_contextual_delta={recommendation.target.contextual_delta:.6f}",
                        *recommendation.rationale,
                    ),
                )

        return recommendation

    def _use_reason(
        self,
        state,
        *,
        target,
        before,
        after,
        required_per_hand: float,
    ) -> str | None:
        thresholds = self._use_thresholds_for_state(state)
        blind = getattr(state, "blind", None)
        remaining = float(getattr(blind, "requirement", 0)) - float(
            getattr(state, "score", 0)
        )
        if remaining <= self.EPSILON:
            return None

        before_clear = float(before.clear_probability)
        after_clear = float(after.clear_probability)
        if (
            after_clear
            > before_clear
            + float(thresholds.minimum_clear_probability_gain)
            + self.EPSILON
        ):
            return "consumable increases current best-play clear probability"

        before_score = float(before.expected_hand_score)
        after_score = float(after.expected_hand_score)
        score_gain = after_score - before_score
        if (
            before_score + self.EPSILON < required_per_hand
            and after_score + self.EPSILON >= required_per_hand
            and score_gain + self.EPSILON
            >= float(thresholds.minimum_pace_score_gain)
        ):
            return "consumable raises visible best play to the blind-clear pace requirement"

        full_slots = (
            len(getattr(state, "consumables", ()))
            >= int(getattr(state, "consumable_slots", 0))
            > 0
        )
        if (
            full_slots
            and float(target.contextual_delta)
            > float(thresholds.minimum_full_slot_contextual_delta) + self.EPSILON
            and after_score + self.EPSILON >= before_score
        ):
            return "consumable realizes positive build value without reducing visible best-play score"

        if (
            int(getattr(state, "hands_remaining", 0)) <= 1
            and score_gain
            > float(thresholds.minimum_final_hand_score_gain) + self.EPSILON
        ):
            return "final hand gains immediate projected score from consumable"

        return None

    def _recommend_planet_d7(
        self,
        state,
        consumable: object,
    ) -> ConsumableTimingRecommendation:
        decision = self.planet_policy.recommend(state, consumable)
        return ConsumableTimingRecommendation(
            decision=decision.decision,
            consumable=consumable,
            target=None,
            before_projection=decision.before_projection,
            after_projection=decision.after_projection,
            required_per_hand=decision.required_per_hand,
            immediate_gain=decision.immediate_score_gain,
            rationale=decision.rationale,
        )

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