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

    Hex chooses one owned Joker uniformly, makes that Joker Polychrome, and removes
    the others under the framework's modeled semantics. Every branch is evaluated
    against the same current-build baseline with the B3 representative probe set.
    No Balatro RNG sample or seed is observed.
    """

    def __init__(
        self,
        *,
        scorer: BalatroScorer | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.scorer = scorer or BalatroScorer()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state) -> HexExpectation:
        jokers = list(getattr(state, "jokers", ()))
        if not jokers:
            return HexExpectation(
                available=False,
                complete=True,
                branch_count=0,
                expected_build_gain=0.0,
                rationale=("Hex has no public Joker target",),
            )

        branch_gains: list[float] = []
        branch_notes: list[str] = []
        for index in range(len(jokers)):
            gain = self._branch_build_gain(state, index=index)
            if gain is None:
                return HexExpectation(
                    available=True,
                    complete=False,
                    branch_count=len(branch_gains),
                    expected_build_gain=0.0,
                    rationale=(
                        "Hex expectation failed closed on an incomplete Joker branch",
                    ),
                )
            branch_gains.append(gain)
            branch_notes.append(f"Joker index {index} B3 Hex branch gain={gain:.3f}")

        expected = sum(branch_gains) / len(branch_gains)
        return HexExpectation(
            available=True,
            complete=True,
            branch_count=len(branch_gains),
            expected_build_gain=expected,
            rationale=(
                f"uniform public Joker branches={len(branch_gains)}",
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

            if not (0 <= index < len(getattr(after_state, "jokers", ()))):
                return None
            chosen = after_state.jokers[index]
            chosen.edition = "Polychrome"
            after_state.jokers = [chosen]

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
