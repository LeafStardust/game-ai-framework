from __future__ import annotations

from dataclasses import dataclass

from games.balatro.build.joker_value import JokerBuildValueEvaluator
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.perkeo import PerkeoJoker
from games.balatro.jokers.triboulet import TribouletJoker
from games.balatro.jokers.yorick import YorickJoker


@dataclass(frozen=True)
class SoulLegendaryOutcome:
    joker_name: str
    build_gain: float


@dataclass(frozen=True)
class SoulExpectation:
    available: bool
    complete: bool
    expected_build_gain: float
    outcomes: tuple[SoulLegendaryOutcome, ...] = ()
    rationale: tuple[str, ...] = ()


class SoulExpectationEvaluator:
    """Evaluate The Soul from its modeled random Legendary-Joker outcomes.

    Soul's result is random, but the public outcome set is finite. Treat each of
    Balatro's five Legendary Jokers as an equally likely branch and value every
    branch with the same B3 whole-build evaluator used for ordinary Joker
    acquisition. This keeps literal scoring, current build context, and modeled
    prospective mechanics authoritative instead of assigning Soul a synthetic
    fixed option score or an Ante-only premium.
    """

    LEGENDARY_FACTORIES = (
        CanioJoker,
        ChicotJoker,
        PerkeoJoker,
        TribouletJoker,
        YorickJoker,
    )

    def __init__(self, *, build_value: JokerBuildValueEvaluator | None = None) -> None:
        self.build_value = build_value or JokerBuildValueEvaluator()

    def evaluate(self, state) -> SoulExpectation:
        joker_slots = max(0, int(getattr(state, "joker_slots", 5) or 5))
        owned = len(tuple(getattr(state, "jokers", ()) or ()))
        if owned >= joker_slots:
            return SoulExpectation(
                available=False,
                complete=True,
                expected_build_gain=0.0,
                rationale=(f"no free Joker slot ({owned}/{joker_slots})",),
            )

        outcomes: list[SoulLegendaryOutcome] = []
        notes: list[str] = []
        try:
            for factory in self.LEGENDARY_FACTORIES:
                joker = factory()
                evaluation = self.build_value.evaluate(state, joker)
                gain = float(evaluation.total_gain)
                outcomes.append(
                    SoulLegendaryOutcome(
                        joker_name=type(joker).__name__,
                        build_gain=gain,
                    )
                )
                notes.append(f"{type(joker).__name__} build gain={gain:.3f}")
        except (AttributeError, TypeError, ValueError) as exc:
            return SoulExpectation(
                available=True,
                complete=False,
                expected_build_gain=0.0,
                outcomes=tuple(outcomes),
                rationale=(
                    "Legendary branch evaluation incomplete",
                    f"{type(exc).__name__}: {exc}",
                    *notes,
                ),
            )

        if not outcomes:
            return SoulExpectation(
                available=True,
                complete=False,
                expected_build_gain=0.0,
                rationale=("no modeled Legendary outcomes",),
            )

        expected = sum(outcome.build_gain for outcome in outcomes) / len(outcomes)
        return SoulExpectation(
            available=True,
            complete=True,
            expected_build_gain=expected,
            outcomes=tuple(outcomes),
            rationale=(
                "uniform expectation over Balatro's five modeled Legendary Jokers",
                f"expected Legendary build gain={expected:.3f}",
                *notes,
            ),
        )
