from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import SKIP_BOOSTER
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.live.consumable_timing_core import ConsumableTargetThresholds
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks


@dataclass(frozen=True)
class PackChoiceThresholds:
    """Thresholds owned only by D9 visible booster-pack choice."""

    skip_bias: float = 0.35

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object] | None,
    ) -> "PackChoiceThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D9 pack-choice threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})


class PlaybookPackTargetEvaluator:
    """Apply D10 admission to the same B6 target ranking used by D6.

    The underlying deterministic target evaluator remains the single source of
    target quality. D10 only adds a pack-specific admission threshold using the
    existing ``ConsumableTargetThresholds`` contract; it does not create another
    target-value scale.
    """

    def __init__(
        self,
        *,
        evaluator=None,
        thresholds: ConsumableTargetThresholds | None = None,
    ) -> None:
        self.evaluator = evaluator or ContextualConsumableTargetEvaluator()
        self.thresholds = thresholds

    def _thresholds_for_state(self, state) -> ConsumableTargetThresholds:
        if self.thresholds is not None:
            return self.thresholds
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D10")
        except BalatroPlaybookNotFound:
            block = {}
        return ConsumableTargetThresholds.from_mapping(block)

    def recommend(self, state, consumable):
        evaluation = self.evaluator.recommend(state, consumable)
        if evaluation is None:
            return None
        if not self._thresholds_for_state(state).accepts(evaluation):
            return None
        return evaluation


class PlaybookBalatroPackPolicy(BalatroPackPolicy):
    """D9/D10 cartridge adapter over the existing pack mechanics policy.

    Explicit constructor thresholds remain authoritative for tests/tools. Otherwise
    the observed deck/stake selects D9 skip bias and D10 target admission on every
    decision, so a future cartridge can retune pack behavior without replacing the
    shared pack implementation.
    """

    def __init__(
        self,
        *,
        skip_bias: float | None = None,
        target_thresholds: ConsumableTargetThresholds | None = None,
        consumable_target_evaluator=None,
        **kwargs,
    ) -> None:
        self._skip_bias_override = (
            None if skip_bias is None else float(skip_bias)
        )
        wrapped_target_evaluator = PlaybookPackTargetEvaluator(
            evaluator=consumable_target_evaluator,
            thresholds=target_thresholds,
        )
        super().__init__(
            skip_bias=0.35 if skip_bias is None else float(skip_bias),
            consumable_target_evaluator=wrapped_target_evaluator,
            **kwargs,
        )

    def skip_bias_for_state(self, state) -> float:
        if self._skip_bias_override is not None:
            return self._skip_bias_override
        try:
            block = default_balatro_playbooks().for_state(state).thresholds_for("D9")
        except BalatroPlaybookNotFound:
            block = {}
        return float(PackChoiceThresholds.from_mapping(block).skip_bias)

    def score_action(self, state, action):
        if action.name == SKIP_BOOSTER:
            bias = self.skip_bias_for_state(state)
            return PackActionScore(
                action,
                bias,
                (f"skip booster; D9 skip_bias={bias:.3f}",),
            )
        return super().score_action(state, action)
