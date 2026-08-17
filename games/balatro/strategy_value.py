from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.build.consumable_synergy import ContextualConsumableSynergyEvaluator
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator

from .strategy import BRONZE, GOLD, SILVER, BalatroStrategyTracker
from .strategy_compat import NeutralLegacyPlaystyleIntentTracker


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
    """Ordinary Joker value plus the universal playbook strategy adjustment.

    The legacy playstyle-affinity tracker is deliberately neutralized here. Direct
    scoring and contextual B3 value remain intact, but universal playbooks are the
    only strategic direction signal in the v1.0 strategy-aware production path.
    """

    def __init__(self, *args, strategy_tracker: BalatroStrategyTracker, **kwargs) -> None:
        kwargs["intent_tracker"] = NeutralLegacyPlaystyleIntentTracker()
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
                "legacy playstyle strategy influence=0.000 in universal-strategy path",
                f"environment-adjusted universal strategy value={strategic.value:+.3f}",
                f"strategy-adjusted whole-build gain={total:.3f}",
            ),
        )


class StrategyAwareConsumableSynergyEvaluator(ContextualConsumableSynergyEvaluator):
    """B4 consumable value under the universal strategy feedback loop.

    Planets are evidence-gated reinforcers. Tarot and Spectral cards may seed a run
    early from ordinary/contextual value, then become progressively less attractive
    when they only advance strategies outside an established shortlist.
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
            rationale_parts = [
                *base.rationale,
                *strategic.rationale,
            ]

            # Tarot/Spectral effects are legitimate early strategy seeders. Once a
            # run has an established direction, however, mapped structural effects
            # that advance no shortlisted strategy pay an increasing opportunity
            # penalty. This is intentionally not a hard ban: sufficiently strong
            # immediate/contextual value may still outweigh the penalty.
            ante = max(1, int(getattr(state, "ante", 1) or 1))
            resolution = self.strategy_tracker.observe(state)
            positive_relationship = strategic.tier in {GOLD, SILVER, BRONZE}
            if (
                category in {"TAROT", "SPECTRAL"}
                and ante >= 3
                and resolution.dominant_strategy_id is not None
                and positive_relationship
                and not strategic.active_alignment
            ):
                config = self.strategy_tracker._config(state)
                if ante >= 6:
                    penalty = self.strategy_tracker._number(
                        config,
                        "late_off_strategy_consumable_penalty",
                        3.0,
                    )
                    phase = "late"
                else:
                    penalty = self.strategy_tracker._number(
                        config,
                        "mid_off_strategy_consumable_penalty",
                        0.75,
                    )
                    phase = "convergence"
                adjustment -= max(0.0, penalty)
                rationale_parts.append(
                    f"{phase} off-shortlist {category} penalty={max(0.0, penalty):.3f}"
                )
            elif category in {"TAROT", "SPECTRAL"} and ante <= 2:
                rationale_parts.append(
                    f"early {category} remains exploration-eligible; no off-strategy penalty"
                )

            rationale_parts.append(
                f"environment strategy adjustment={adjustment:+.3f}"
            )
            rationale = tuple(rationale_parts)

        return StrategyAdjustedConsumableEvaluation(
            total_gain=float(base.total_gain) + adjustment,
            rationale=tuple(rationale),
            base_evaluation=base,
            strategic_adjustment=adjustment,
        )
