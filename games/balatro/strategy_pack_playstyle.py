from __future__ import annotations

from dataclasses import replace

from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.strategy import BalatroStrategyTracker


class StrategyAwarePackPlaystyleEvaluator(PackPlaystyleEvaluator):
    """D9 direct choice value with universal-strategy priority for Planets."""

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def evaluate(self, state, *, kind: str, target=None, rank=None, suit=None):
        base = super().evaluate(
            state,
            kind=kind,
            target=target,
            rank=rank,
            suit=suit,
        )
        if str(kind).upper() != "PLANET":
            return base

        strategic = self.strategy_tracker.evaluate_item(
            state,
            target,
            kind="PLANET",
        )
        # Planets refine the selected hand plan. They are not allowed to create a
        # new strategy merely because the pack happened to offer one.
        if strategic.tier is None or not strategic.active_alignment:
            value = min(0.0, float(base.value)) - 4.0
            return replace(
                base,
                fit=-1.0,
                value=value,
                rationale=(
                    *base.rationale,
                    *strategic.rationale,
                    (
                        "D9 Planet is outside every enabled universal strategy"
                        if strategic.tier is None
                        else "D9 Planet does not match the active universal strategy"
                    ),
                ),
            )

        value = float(base.value) + float(strategic.value)
        fit = max(float(base.fit), min(1.0, float(strategic.value) / 8.0))
        return replace(
            base,
            fit=fit,
            value=value,
            rationale=(
                *base.rationale,
                *strategic.rationale,
                f"D9 environment-adjusted strategy value={strategic.value:+.3f}",
            ),
        )
