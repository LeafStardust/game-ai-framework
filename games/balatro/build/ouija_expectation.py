from __future__ import annotations

"""Analytic public-state value for Ouija.

Ouija rewrites every current hand card to one uniformly selected rank and permanently
reduces hand size by one.  The rank branch is finite (13 equal outcomes), and the
permanent cost is delegated to ``HandSizeOpportunityEvaluator`` so no fixed hand-size
penalty is invented.

Immediate rewrite benefit is measured through the same final literal/stochastic
play projector used by live D1: compare the best legal play from the current public
hand against the best legal play after each rank rewrite.  Relative expected score
gain is converted with the existing D2 direct-scoring weight/cap, then the shared
D2-scale hand-size opportunity cost is subtracted.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.build.joker_strategy import JokerBuildValueWeights
from games.balatro.card_selector import CardSelector
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")


@dataclass(frozen=True)
class OuijaExpectation:
    available: bool
    complete: bool
    expected_rewrite_relative_gain: float
    rewrite_build_value: float
    hand_size_cost: float
    expected_total_gain: float
    rationale: tuple[str, ...] = ()


class OuijaExpectationEvaluator:
    def __init__(
        self,
        *,
        hand_size: HandSizeOpportunityEvaluator | None = None,
        hand_evaluator: LiveHandDecisionEvaluator | None = None,
        selector: CardSelector | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.hand_size = hand_size or HandSizeOpportunityEvaluator()
        self.hand_evaluator = hand_evaluator or LiveHandDecisionEvaluator()
        self.selector = selector or CardSelector()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state) -> OuijaExpectation:
        hand = list(getattr(state, "hand", ()) or ())
        if len(hand) <= 1:
            return OuijaExpectation(
                available=False,
                complete=True,
                expected_rewrite_relative_gain=0.0,
                rewrite_build_value=0.0,
                hand_size_cost=0.0,
                expected_total_gain=0.0,
                rationale=("Ouija requires more than one public hand card",),
            )

        before = self._best_score(state)
        if before is None:
            return OuijaExpectation(
                available=True,
                complete=False,
                expected_rewrite_relative_gain=0.0,
                rewrite_build_value=0.0,
                hand_size_cost=0.0,
                expected_total_gain=0.0,
                rationale=("Ouija failed closed on current-hand literal score projection",),
            )

        branch_relative: list[float] = []
        branch_notes: list[str] = []
        for rank in RANKS:
            projected = deepcopy(state)
            for card in projected.hand:
                card.rank = rank
            after = self._best_score(projected)
            if after is None:
                return OuijaExpectation(
                    available=True,
                    complete=False,
                    expected_rewrite_relative_gain=0.0,
                    rewrite_build_value=0.0,
                    hand_size_cost=0.0,
                    expected_total_gain=0.0,
                    rationale=(f"Ouija failed closed on rank branch {rank}",),
                )
            relative = (float(after) - float(before)) / max(abs(float(before)), 1.0)
            branch_relative.append(relative)
            branch_notes.append(f"rank {rank} best-play relative gain={relative:.6f}")

        expected_relative = sum(branch_relative) / float(len(branch_relative))
        rewrite_value = max(
            -self.weights.direct_scoring_cap,
            min(
                self.weights.direct_scoring_cap,
                expected_relative * self.weights.direct_scoring_gain,
            ),
        )

        hand_size = self.hand_size.evaluate(state, penalty=1)
        if not hand_size.available or not hand_size.complete:
            return OuijaExpectation(
                available=True,
                complete=False,
                expected_rewrite_relative_gain=expected_relative,
                rewrite_build_value=rewrite_value,
                hand_size_cost=0.0,
                expected_total_gain=0.0,
                rationale=(
                    "Ouija rank expectation is complete but permanent hand-size cost is unavailable",
                    *hand_size.rationale,
                ),
            )

        total = rewrite_value - float(hand_size.build_value_loss)
        return OuijaExpectation(
            available=True,
            complete=True,
            expected_rewrite_relative_gain=expected_relative,
            rewrite_build_value=rewrite_value,
            hand_size_cost=float(hand_size.build_value_loss),
            expected_total_gain=total,
            rationale=(
                f"Ouija public hand cards={len(hand)}",
                "Ouija rank probabilities=13 ranks uniformly at 1/13 each",
                f"current best literal play={before:.3f}",
                *branch_notes,
                f"expected rank-rewrite relative gain={expected_relative:.6f}",
                f"D2-scale rank-rewrite value={rewrite_value:.3f}",
                *hand_size.rationale,
                f"Ouija net build value={total:.3f}",
            ),
        )

    def _best_score(self, state) -> float | None:
        best = None
        for action in self.selector.generate_play_actions(state):
            try:
                projection = self.hand_evaluator.project_play(state, action)
            except (
                AttributeError,
                IndexError,
                KeyError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                return None
            if not projection.joker_projection_complete:
                return None
            value = float(projection.expected_hand_score)
            if best is None or value > best:
                best = value
        return best
