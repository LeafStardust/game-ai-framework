from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.build.consumable_synergy import ContextualConsumableSynergyEvaluator
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator

from .strategy import BalatroStrategyTracker


@dataclass(frozen=True)
class StrategyAdjustedConsumableEvaluation:
    """B4 consumable value plus universal-strategy environment adjustment."""

    total_gain: float
    rationale: tuple[str, ...]
    base_evaluation: object
    strategic_adjustment: float

    @property
    def build_path_gain(self):
        return self.base_evaluation.build_path_gain

    @property
    def paths(self):
        return self.base_evaluation.paths

    @property
    def contributions(self):
        return self.base_evaluation.contributions

    @property
    def descriptor(self):
        return self.base_evaluation.descriptor


class StrategyAwareJokerBuildValueEvaluator(JokerBuildValueEvaluator):
    """Add explicit universal-strategy component priority to ordinary B3 value."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def evaluate(self, state, joker):
        base = super().evaluate(state, joker)
        strategic = self.strategy_tracker.evaluate_item(
            state,
            joker,
            kind="JOKER",
        )
        total = float(base.total_gain) + float(strategic.value)
        return replace(
            base,
            total_gain=total,
            rationale=(
                *base.rationale,
                *strategic.rationale,
                f"environment-adjusted universal strategy value={strategic.value:+.3f}",
                f"strategy-adjusted whole-build gain={total:.3f}",
            ),
        )


class StrategyAwareConsumableSynergyEvaluator(ContextualConsumableSynergyEvaluator):
    """B4 value that blocks irrelevant Planets and rewards strategy components."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def evaluate(self, candidate, state, *, profile=None):
        base = super().evaluate(candidate, state, profile=profile)
        category = str(getattr(candidate, "category", "")).upper()
        kind = "PLANET" if category == "PLANET" else "CONSUMABLE"
        strategic = self.strategy_tracker.evaluate_item(
            state,
            candidate,
            kind=kind,
        )

        if kind == "PLANET" and (
            strategic.tier is None or not strategic.active_alignment
        ):
            # Planets refine an already-selected hand strategy; they do not choose
            # the strategy. This is the direct guard against random Neptune/Jupiter
            # fishing from a neutral run.
            adjustment = -max(4.0, float(base.total_gain) + 1.0)
            rationale = (
                *base.rationale,
                *strategic.rationale,
                (
                    "Planet blocked because no enabled universal strategy values it"
                    if strategic.tier is None
                    else "Planet blocked because its universal strategy is not active"
                ),
                f"environment strategy adjustment={adjustment:+.3f}",
            )
        else:
            adjustment = float(strategic.value)
            rationale = (
                *base.rationale,
                *strategic.rationale,
                f"environment strategy adjustment={adjustment:+.3f}",
            )

        return StrategyAdjustedConsumableEvaluation(
            total_gain=float(base.total_gain) + adjustment,
            rationale=tuple(rationale),
            base_evaluation=base,
            strategic_adjustment=adjustment,
        )
