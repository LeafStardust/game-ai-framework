from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import (
    JokerBuildValueEvaluator,
    JokerBuildValueWeights,
)
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class HexExpectation:
    """Analytic public-state value for Hex's random surviving Joker branch."""

    available: bool
    complete: bool
    branch_count: int
    expected_build_gain: float
    rationale: tuple[str, ...] = ()


class HexExpectationEvaluator:
    """Enumerate Hex outcomes using B3 representative whole-build scoring.

    Hex chooses uniformly from owned Jokers that do not already have an Edition,
    makes the chosen Joker Polychrome, and destroys every other non-Eternal Joker.
    Eternal Jokers survive even when they are not selected. Every eligible branch
    is evaluated against the same current-build baseline with the B3 representative
    probe set. No Balatro RNG sample or seed is observed.
    """

    def __init__(
        self,
        *,
        scorer: BalatroScorer | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.scorer = scorer or BalatroScorer()
        self.weights = weights or JokerBuildValueWeights()

    @staticmethod
    def _eligible_indices(jokers) -> tuple[int, ...]:
        return tuple(
            index
            for index, joker in enumerate(jokers)
            if getattr(joker, "edition", None) in (None, "")
        )

    def evaluate(self, state) -> HexExpectation:
        jokers = list(getattr(state, "jokers", ()))
        eligible = self._eligible_indices(jokers)
        if not eligible:
            return HexExpectation(
                available=False,
                complete=True,
                branch_count=0,
                expected_build_gain=0.0,
                rationale=("Hex has no editionless public Joker target",),
            )

        branch_gains: list[float] = []
        branch_notes: list[str] = []
        for index in eligible:
            gain = self._branch_build_gain(state, index=index)
            if gain is None:
                return HexExpectation(
                    available=True,
                    complete=False,
                    branch_count=len(branch_gains),
                    expected_build_gain=0.0,
                    rationale=(
                        "Hex expectation failed closed on an incomplete eligible Joker branch",
                    ),
                )
            branch_gains.append(gain)
            branch_notes.append(
                f"eligible Joker index {index} B3 Hex branch gain={gain:.3f}"
            )

        expected = sum(branch_gains) / len(branch_gains)
        eternal_count = sum(
            bool(getattr(joker, "eternal", False))
            for joker in jokers
        )
        return HexExpectation(
            available=True,
            complete=True,
            branch_count=len(branch_gains),
            expected_build_gain=expected,
            rationale=(
                f"uniform editionless Joker branches={len(branch_gains)}",
                f"Eternal Jokers preserved={eternal_count}",
                *branch_notes,
                f"expected B3 Hex whole-build gain={expected:.3f}",
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

            after_jokers = list(getattr(after_state, "jokers", ()))
            if not (0 <= index < len(after_jokers)):
                return None
            chosen = after_jokers[index]
            if getattr(chosen, "edition", None) not in (None, ""):
                return None

            chosen.edition = "Polychrome"
            after_state.jokers = [
                joker
                for joker_index, joker in enumerate(after_jokers)
                if joker_index == index or bool(getattr(joker, "eternal", False))
            ]

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
