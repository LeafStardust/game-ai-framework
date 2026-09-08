from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import (
    JokerBuildValueEvaluator,
    JokerBuildValueWeights,
)
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class AnkhExpectation:
    """Analytic public-state value for Ankh's random copied-Joker branch."""

    available: bool
    complete: bool
    branch_count: int
    expected_build_gain: float
    rationale: tuple[str, ...] = ()


class AnkhExpectationEvaluator:
    """Enumerate Ankh outcomes using B3 representative whole-build scoring.

    Ankh chooses one owned Joker uniformly, creates a copy, then destroys every
    nonchosen non-Eternal Joker. Negative is not retained by the created copy.
    Every branch is scored against the same current-build baseline with B3's
    representative probes. No Balatro RNG sample or seed is observed.
    """

    def __init__(
        self,
        *,
        scorer: BalatroScorer | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.scorer = scorer or BalatroScorer()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state) -> AnkhExpectation:
        jokers = list(getattr(state, "jokers", ()))
        if not jokers:
            return AnkhExpectation(
                available=False,
                complete=True,
                branch_count=0,
                expected_build_gain=0.0,
                rationale=("Ankh has no public Joker target",),
            )

        branch_gains: list[float] = []
        branch_notes: list[str] = []
        for index in range(len(jokers)):
            gain = self._branch_build_gain(state, index=index)
            if gain is None:
                return AnkhExpectation(
                    available=True,
                    complete=False,
                    branch_count=len(branch_gains),
                    expected_build_gain=0.0,
                    rationale=(
                        "Ankh expectation failed closed on an incomplete Joker branch",
                    ),
                )
            branch_gains.append(gain)
            branch_notes.append(f"Joker index {index} B3 Ankh branch gain={gain:.3f}")

        expected = sum(branch_gains) / len(branch_gains)
        return AnkhExpectation(
            available=True,
            complete=True,
            branch_count=len(branch_gains),
            expected_build_gain=expected,
            rationale=(
                f"uniform public Joker branches={len(branch_gains)}",
                *branch_notes,
                f"expected B3 Ankh whole-build gain={expected:.3f}",
            ),
        )

    def _branch_build_gain(self, state, *, index: int) -> float | None:
        relative_gains: list[float] = []
        for hand, template_cards in JokerBuildValueEvaluator.PROBES:
            before_state = copy.deepcopy(state)
            after_state = copy.deepcopy(state)
            before_cards = copy.deepcopy(list(template_cards))
            after_cards = copy.deepcopy(list(template_cards))
            before_state.hand = before_cards
            after_state.hand = after_cards

            jokers = list(getattr(after_state, "jokers", ()))
            if not (0 <= index < len(jokers)):
                return None

            chosen = jokers[index]
            created = copy.deepcopy(chosen)
            if str(getattr(created, "edition", "") or "").upper() == "NEGATIVE":
                created.edition = None

            survivors = [
                joker
                for survivor_index, joker in enumerate(jokers)
                if survivor_index == index or bool(getattr(joker, "eternal", False))
            ]
            after_state.jokers = [*survivors, created]

            try:
                before = self.scorer.score(
                    hand,
                    state=before_state,
                    cards=before_cards,
                    include_card_chips=True,
                    resolve_random_effects=False,
                ).total
                after = self.scorer.score(
                    hand,
                    state=after_state,
                    cards=after_cards,
                    include_card_chips=True,
                    resolve_random_effects=False,
                ).total
            except (
                AttributeError,
                IndexError,
                KeyError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                return None

            relative_gains.append(
                (float(after) - float(before)) / max(abs(float(before)), 1.0)
            )

        if not relative_gains:
            return None

        direct_gain = sum(relative_gains) / len(relative_gains)
        return max(
            -self.weights.direct_scoring_cap,
            min(
                self.weights.direct_scoring_cap,
                direct_gain * self.weights.direct_scoring_gain,
            ),
        )
