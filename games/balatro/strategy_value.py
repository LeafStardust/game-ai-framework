from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.build.consumable_synergy import ContextualConsumableSynergyEvaluator
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator

from .strategy import BalatroStrategyTracker


@dataclass(frozen=True)
class StrategyAdjustedConsumableEvaluation:
    """D4-facing consumable value with explicit cartridge-strategy adjustment."""

    total_gain: float
    rationale: tuple[str, ...]
    base_evaluation: object
    strategic_adjustment: float


class StrategyAwareJokerBuildValueEvaluator(JokerBuildValueEvaluator):
    """Add explicit cartridge component priority to ordinary B3 Joker value."""

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
                f"cartridge strategy adjustment={strategic.value:+.3f}",
                f"strategy-adjusted whole-build gain={total:.3f}",
            ),
        )


class StrategyAwareConsumableSynergyEvaluator(ContextualConsumableSynergyEvaluator):
    """D4 value that refuses unsupported Planets and rewards strategy pieces.

    Generic Tarot/Spectral utility remains available through B4. Planets are the
    deliberate exception: a hand-level upgrade is not sufficient reason to buy one
    unless at least one cartridge strategy explicitly values that Planet. This keeps
    speculative lines such as Neptune out of ordinary Red/White shops while still
    allowing a future cartridge to define a real Straight Flush strategy.
    """

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

        if kind == "PLANET" and strategic.tier is None:
            # D4 requires positive build gain for a purchase. Drive unsupported
            # Planets below zero regardless of their generic HAND_LEVEL intrinsic
            # value instead of letting that local effect create random build drift.
            adjustment = -max(4.0, float(base.total_gain) + 1.0)
            rationale = (
                *base.rationale,
                *strategic.rationale,
                "unsupported Planet blocked by cartridge strategy catalog",
                f"cartridge strategy adjustment={adjustment:+.3f}",
            )
        else:
            adjustment = float(strategic.value)
            rationale = (
                *base.rationale,
                *strategic.rationale,
                f"cartridge strategy adjustment={adjustment:+.3f}",
            )

        return StrategyAdjustedConsumableEvaluation(
            total_gain=float(base.total_gain) + adjustment,
            rationale=tuple(rationale),
            base_evaluation=base,
            strategic_adjustment=adjustment,
        )
