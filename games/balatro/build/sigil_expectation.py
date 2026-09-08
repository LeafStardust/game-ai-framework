from __future__ import annotations

from dataclasses import dataclass

from games.balatro.build.playing_card_synergy import (
    ContextualPlayingCardSynergyEvaluator,
)
from games.balatro.build.profile import BalatroBuildProfiler


@dataclass(frozen=True)
class SigilExpectation:
    """Analytic public-state value for Sigil's uniform random suit rewrite."""

    available: bool
    complete: bool
    expected_contextual_gain: float
    expected_total_gain: float
    rationale: tuple[str, ...] = ()


class SigilExpectationEvaluator:
    """Value Sigil by enumerating all four equally likely suit outcomes.

    Sigil rewrites every visible hand card to one uniformly selected suit. The
    evaluator scores each complete public outcome through the existing B6
    playing-card build-context model and never samples Balatro RNG or reads a seed.
    """

    SUIT_OUTCOMES = (
        ("Hearts", 0.25),
        ("Diamonds", 0.25),
        ("Clubs", 0.25),
        ("Spades", 0.25),
    )

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        card_evaluator: ContextualPlayingCardSynergyEvaluator | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.card_evaluator = card_evaluator or ContextualPlayingCardSynergyEvaluator(
            profiler=self.profiler
        )

    def evaluate(self, state) -> SigilExpectation:
        hand = list(getattr(state, "hand", ()))
        if len(hand) <= 1:
            return SigilExpectation(
                available=False,
                complete=True,
                expected_contextual_gain=0.0,
                expected_total_gain=0.0,
                rationale=(
                    "Sigil requires more than one public hand card",
                ),
            )

        profile = self.profiler.profile(state)
        try:
            before = sum(
                float(
                    self.card_evaluator.evaluate(
                        state,
                        rank=card.rank,
                        suit=card.suit,
                        enhancement=card.enhancement,
                        seal=card.seal,
                        edition=card.edition,
                        profile=profile,
                    ).total_gain
                )
                for card in hand
            )

            expected_gain = 0.0
            branch_notes: list[str] = []
            for suit, probability in self.SUIT_OUTCOMES:
                after = sum(
                    float(
                        self.card_evaluator.evaluate(
                            state,
                            rank=card.rank,
                            suit=suit,
                            enhancement=card.enhancement,
                            seal=card.seal,
                            edition=card.edition,
                            profile=profile,
                        ).total_gain
                    )
                    for card in hand
                )
                branch_gain = after - before
                expected_gain += probability * branch_gain
                branch_notes.append(f"{suit} B6 rewrite gain={branch_gain:.3f}")
        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            ZeroDivisionError,
        ):
            return SigilExpectation(
                available=True,
                complete=False,
                expected_contextual_gain=0.0,
                expected_total_gain=0.0,
                rationale=(
                    "Sigil expectation failed closed on an incomplete suit branch",
                ),
            )

        return SigilExpectation(
            available=True,
            complete=True,
            expected_contextual_gain=expected_gain,
            expected_total_gain=expected_gain,
            rationale=(
                f"Sigil rewrites public hand cards={len(hand)}",
                "Sigil suit probabilities=Hearts/Diamonds/Clubs/Spades=1/4 each",
                *branch_notes,
                f"expected B6 Sigil rewrite gain={expected_gain:.3f}",
            ),
        )
