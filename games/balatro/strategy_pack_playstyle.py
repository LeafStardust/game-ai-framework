from __future__ import annotations

from dataclasses import replace

from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.strategy import BRONZE, GOLD, SILVER, BalatroStrategyTracker
from games.balatro.strategy_compat import NeutralLegacyPlaystyleIntentTracker


class StrategyAwarePackPlaystyleEvaluator(PackPlaystyleEvaluator):
    """D9 choice value with universal-strategy priority.

    The legacy playstyle vector is neutralized in this subclass. Planet choices are
    already evaluated against universal playbooks; other pack-choice strategy
    signals are added explicitly as their playbook integrations are implemented.
    """

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        kwargs["intent_tracker"] = NeutralLegacyPlaystyleIntentTracker()
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
        normalized_kind = str(kind).upper()
        if normalized_kind not in {"PLANET", "TAROT", "SPECTRAL"}:
            return replace(
                base,
                rationale=(
                    *base.rationale,
                    "D9 legacy playstyle strategy influence=0.000 in universal-strategy path",
                ),
            )

        strategic = self.strategy_tracker.evaluate_item(
            state,
            target,
            kind="PLANET" if normalized_kind == "PLANET" else "CONSUMABLE",
        )
        # Planets refine an evidenced hand plan. They are not allowed to create a
        # new strategy merely because the pack happened to offer one.
        if normalized_kind == "PLANET" and (
            strategic.tier is None or not strategic.active_alignment
        ):
            value = min(0.0, float(base.value)) - 4.0
            return replace(
                base,
                fit=-1.0,
                value=value,
                rationale=(
                    *base.rationale,
                    "D9 legacy playstyle strategy influence=0.000 in universal-strategy path",
                    *strategic.rationale,
                    (
                        "D9 Planet is outside every enabled universal strategy"
                        if strategic.tier is None
                        else "D9 Planet does not match the active universal strategy"
                    ),
                ),
            )

        adjustment = float(strategic.value)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        resolution = self.strategy_tracker.observe(state)
        positive_relationship = strategic.tier in {GOLD, SILVER, BRONZE}
        if (
            normalized_kind in {"TAROT", "SPECTRAL"}
            and ante >= 3
            and resolution.dominant_strategy_id is not None
            and positive_relationship
            and not strategic.active_alignment
        ):
            config = self.strategy_tracker._config(state)
            key = (
                "late_off_strategy_consumable_penalty"
                if ante >= 6
                else "mid_off_strategy_consumable_penalty"
            )
            default = 3.0 if ante >= 6 else 0.75
            adjustment -= max(
                0.0,
                self.strategy_tracker._number(config, key, default),
            )

        value = float(base.value) + adjustment
        fit = max(float(base.fit), min(1.0, float(strategic.value) / 8.0))
        return replace(
            base,
            fit=fit,
            value=value,
            rationale=(
                *base.rationale,
                "D9 legacy playstyle strategy influence=0.000 in universal-strategy path",
                *strategic.rationale,
                f"D9 environment-adjusted strategy value={adjustment:+.3f}",
            ),
        )
