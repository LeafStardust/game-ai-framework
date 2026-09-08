from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import (
    JokerBuildValueEvaluator,
    JokerBuildValueWeights,
)
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class WheelExpectation:
    available: bool
    complete: bool
    eligible_indices: tuple[int, ...]
    success_probability: float
    conditional_build_gain: float
    expected_build_gain: float
    rationale: tuple[str, ...] = ()


class WheelOfFortuneExpectationEvaluator:
    """Analytic public-state value for Wheel of Fortune.

    Wheel randomness is represented as a probability distribution only. The model
    never samples Balatro RNG or observes its seed. On success Balatro chooses one
    editionless Joker uniformly, then polls Foil/Holographic/Polychrome with the
    vanilla 50/35/15 conditional weights. Oops! All 6s doubles the listed 1-in-4
    success probability per active copy.

    Edition outcomes are valued by replaying the existing representative whole-build
    scoring probes on isolated copies, using the same direct-scoring scale as B3/B5
    Joker build valuation.
    """

    BASE_SUCCESS_PROBABILITY = 0.25
    EDITION_PROBABILITIES = (
        ("FOIL", 0.50),
        ("HOLOGRAPHIC", 0.35),
        ("POLYCHROME", 0.15),
    )

    def __init__(
        self,
        *,
        scorer: BalatroScorer | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.scorer = scorer or BalatroScorer()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state) -> WheelExpectation:
        jokers = list(getattr(state, "jokers", ()))
        eligible = tuple(
            index
            for index, joker in enumerate(jokers)
            if self._is_editionless(joker)
        )
        probability = self._success_probability(jokers)

        if not eligible:
            return WheelExpectation(
                available=False,
                complete=True,
                eligible_indices=(),
                success_probability=probability,
                conditional_build_gain=0.0,
                expected_build_gain=0.0,
                rationale=("Wheel has no editionless public Joker target",),
            )

        weighted_total = 0.0
        branch_count = 0
        target_weight = 1.0 / len(eligible)
        for index in eligible:
            for edition, edition_probability in self.EDITION_PROBABILITIES:
                value = self._edition_build_gain(state, index=index, edition=edition)
                if value is None:
                    return WheelExpectation(
                        available=True,
                        complete=False,
                        eligible_indices=eligible,
                        success_probability=probability,
                        conditional_build_gain=0.0,
                        expected_build_gain=0.0,
                        rationale=(
                            "Wheel scoring expectation failed closed on an incomplete Joker edition branch",
                        ),
                    )
                weighted_total += target_weight * edition_probability * value
                branch_count += 1

        expected = probability * weighted_total
        oops_count = self._oops_count(jokers)
        return WheelExpectation(
            available=True,
            complete=True,
            eligible_indices=eligible,
            success_probability=probability,
            conditional_build_gain=weighted_total,
            expected_build_gain=expected,
            rationale=(
                f"editionless Joker targets={len(eligible)}",
                f"Wheel success probability={probability:.3f}",
                f"Oops! All 6s probability multipliers={oops_count}",
                "conditional edition weights=Foil 0.50/Holographic 0.35/Polychrome 0.15",
                f"scored edition branches={branch_count}",
                f"conditional whole-build gain={weighted_total:.3f}",
                f"expected whole-build gain={expected:.3f}",
            ),
        )

    def _edition_build_gain(self, state, *, index: int, edition: str) -> float | None:
        gains: list[float] = []
        for hand, template_cards in JokerBuildValueEvaluator.PROBES:
            before_state = copy.deepcopy(state)
            after_state = copy.deepcopy(state)
            before_cards = copy.deepcopy(list(template_cards))
            after_cards = copy.deepcopy(list(template_cards))
            before_state.hand = before_cards
            after_state.hand = after_cards

            if not (0 <= index < len(getattr(after_state, "jokers", ()))):
                return None
            after_state.jokers[index].edition = edition

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

            gains.append((float(after) - float(before)) / max(abs(float(before)), 1.0))

        if not gains:
            return None

        direct_gain = sum(gains) / len(gains)
        return max(
            -self.weights.direct_scoring_cap,
            min(
                self.weights.direct_scoring_cap,
                direct_gain * self.weights.direct_scoring_gain,
            ),
        )

    @classmethod
    def _success_probability(cls, jokers) -> float:
        return min(
            1.0,
            cls.BASE_SUCCESS_PROBABILITY * (2.0 ** cls._oops_count(jokers)),
        )

    @staticmethod
    def _oops_count(jokers) -> int:
        return sum(
            1
            for joker in jokers
            if type(joker).__name__ == "OopsAll6sJoker"
            and not bool(getattr(joker, "debuffed", False))
        )

    @staticmethod
    def _is_editionless(joker) -> bool:
        edition = getattr(joker, "edition", None)
        return edition is None or str(edition).strip() == ""
