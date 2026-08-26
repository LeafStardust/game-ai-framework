from __future__ import annotations

"""Public-mechanics value of a permanent Balatro hand-size reduction.

Ouija and Ectoplasm permanently reduce future hand size.  That cost must not be a
fixed synthetic penalty: the loss depends on the current permanent deck and Joker
build.  This evaluator compares a fresh future draw at the current hand size against
the same public deck/build after a specified reduction.

Draw identities come only from the authoritative unordered permanent deck.  Small
spaces are enumerated exactly and large spaces use the same deterministic
public-composition sampling approach as D1; no Balatro seed, RNG state, or future
draw order is observed.  Each draw is valued by the best legal one-hand play through
the final live literal/stochastic score projector, including the correctly remaining
deck after the draw (important for Blue Joker).

The projection deliberately clears transient current-blind/current-round state.  A
permanent hand-size change persists into later blinds; pricing it under The Mouth,
The Eye, a stale shop-phase Blind object, current-round Card Sharp history, or other
one-round constraints would turn an ordinary future opportunity cost into a function
of state that disappears before the next blind.

The relative expected-score loss is converted with the existing D2 direct-scoring
weight/cap so callers can compare hand-size cost against whole-build Joker gains
without introducing a new utility unit.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import JokerBuildValueWeights
from games.balatro.card_selector import CardSelector
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


@dataclass(frozen=True)
class HandSizeOpportunity:
    available: bool
    complete: bool
    hand_size_before: int
    hand_size_after: int
    expected_best_score_before: float
    expected_best_score_after: float
    relative_score_loss: float
    build_value_loss: float
    exact_before: bool
    exact_after: bool
    rationale: tuple[str, ...] = ()


class HandSizeOpportunityEvaluator:
    """Measure permanent hand-size loss from public future-draw scoring capacity."""

    # Match the live planner's small-space exact boundary but keep the shop-side
    # deterministic sample deliberately bounded: each sampled hand enumerates every
    # legal 1..5-card play through the final score projector.
    EXACT_COMBINATION_LIMIT = 128
    SAMPLE_COUNT = 24

    def __init__(
        self,
        *,
        draw_outcomes: PublicDrawOutcomeModel | None = None,
        hand_evaluator: LiveHandDecisionEvaluator | None = None,
        selector: CardSelector | None = None,
        weights: JokerBuildValueWeights | None = None,
    ) -> None:
        self.draw_outcomes = draw_outcomes or PublicDrawOutcomeModel(
            exact_combination_limit=self.EXACT_COMBINATION_LIMIT,
            sample_count=self.SAMPLE_COUNT,
            seed=0,
        )
        self.hand_evaluator = hand_evaluator or LiveHandDecisionEvaluator()
        self.selector = selector or CardSelector()
        self.weights = weights or JokerBuildValueWeights()

    def evaluate(self, state, *, penalty: int) -> HandSizeOpportunity:
        penalty = max(0, int(penalty))
        before_size = max(0, int(getattr(state, "hand_size", 0) or 0))
        after_size = max(0, before_size - penalty)

        owned = getattr(state, "owned_deck", None)
        if owned is None or not list(owned):
            return HandSizeOpportunity(
                available=False,
                complete=False,
                hand_size_before=before_size,
                hand_size_after=after_size,
                expected_best_score_before=0.0,
                expected_best_score_after=0.0,
                relative_score_loss=0.0,
                build_value_loss=0.0,
                exact_before=False,
                exact_after=False,
                rationale=(
                    "permanent hand-size value unavailable: authoritative owned_deck was not observed",
                ),
            )
        if penalty <= 0 or after_size >= before_size:
            return HandSizeOpportunity(
                available=True,
                complete=True,
                hand_size_before=before_size,
                hand_size_after=after_size,
                expected_best_score_before=0.0,
                expected_best_score_after=0.0,
                relative_score_loss=0.0,
                build_value_loss=0.0,
                exact_before=True,
                exact_after=True,
                rationale=("no permanent hand-size reduction to price",),
            )
        if after_size <= 0:
            return HandSizeOpportunity(
                available=True,
                complete=True,
                hand_size_before=before_size,
                hand_size_after=after_size,
                expected_best_score_before=0.0,
                expected_best_score_after=0.0,
                relative_score_loss=1.0,
                build_value_loss=min(
                    self.weights.direct_scoring_cap,
                    self.weights.direct_scoring_gain,
                ),
                exact_before=True,
                exact_after=True,
                rationale=("hand-size reduction leaves no drawable hand",),
            )

        composition = PublicDeckComposition.from_cards(owned)
        future_state = self._future_blind_state(state)
        before = self._expected_best_score(future_state, composition, before_size)
        after = self._expected_best_score(future_state, composition, after_size)
        if before is None or after is None:
            return HandSizeOpportunity(
                available=True,
                complete=False,
                hand_size_before=before_size,
                hand_size_after=after_size,
                expected_best_score_before=0.0,
                expected_best_score_after=0.0,
                relative_score_loss=0.0,
                build_value_loss=0.0,
                exact_before=False,
                exact_after=False,
                rationale=(
                    "hand-size opportunity model failed closed on an incomplete literal scoring branch",
                ),
            )

        before_score, before_exact = before
        after_score, after_exact = after
        relative_loss = max(
            0.0,
            (float(before_score) - float(after_score))
            / max(abs(float(before_score)), 1.0),
        )
        value_loss = min(
            self.weights.direct_scoring_cap,
            relative_loss * self.weights.direct_scoring_gain,
        )
        return HandSizeOpportunity(
            available=True,
            complete=True,
            hand_size_before=before_size,
            hand_size_after=after_size,
            expected_best_score_before=float(before_score),
            expected_best_score_after=float(after_score),
            relative_score_loss=relative_loss,
            build_value_loss=value_loss,
            exact_before=before_exact,
            exact_after=after_exact,
            rationale=(
                f"future draw hand size {before_size}->{after_size}",
                f"expected best literal play before={before_score:.3f}",
                f"expected best literal play after={after_score:.3f}",
                f"relative scoring-capacity loss={relative_loss:.6f}",
                f"D2-scale hand-size opportunity cost={value_loss:.3f}",
                "future draws use unordered public permanent-deck composition only",
                "transient current-blind and current-round constraints are excluded",
                f"before distribution={'exact' if before_exact else 'deterministic sampled'}",
                f"after distribution={'exact' if after_exact else 'deterministic sampled'}",
            ),
        )

    @staticmethod
    def _future_blind_state(state):
        projected = deepcopy(state)
        projected.phase = "PLAYING"
        projected.score = 0
        projected.blind_score = 0
        projected.blind = None
        projected.boss_name = None
        projected.boss_blind_state_observed = False
        projected.boss_blind_hands = set()
        projected.boss_blind_only_hand = None
        projected.round_most_played_hand = None
        projected.round_hand_play_counts = {
            hand: 0
            for hand in dict(getattr(projected, "hand_levels", {}) or {})
        }
        projected.last_played_hand = None
        projected.hands_remaining = max(1, int(getattr(projected, "hands_remaining", 1) or 1))
        projected.discards_used = 0
        projected.discard_pile = []
        projected.shop_active = False
        projected.shop_jokers = []
        projected.shop_consumables = []
        projected.shop_boosters = []
        projected.shop_vouchers = []
        return projected

    def _expected_best_score(
        self,
        state,
        composition: PublicDeckComposition,
        hand_size: int,
    ) -> tuple[float, bool] | None:
        draws = min(max(0, int(hand_size)), composition.total_cards)
        distribution = self.draw_outcomes.distribution(composition, draws)
        expected = 0.0

        for outcome in distribution.outcomes:
            projected = deepcopy(state)
            projected.score = 0
            projected.hand = [
                self.draw_outcomes.card_from_signature(signature)
                for signature in outcome.cards
            ]
            projected.deck = self.draw_outcomes.remaining_cards(composition, outcome)
            projected.hand_size = draws

            best = None
            for action in self.selector.generate_play_actions(projected):
                try:
                    play = self.hand_evaluator.project_play(projected, action)
                except (
                    AttributeError,
                    IndexError,
                    KeyError,
                    TypeError,
                    ValueError,
                    ZeroDivisionError,
                ):
                    return None
                if not play.joker_projection_complete:
                    return None
                score = float(play.expected_hand_score)
                if best is None or score > best:
                    best = score

            if best is None:
                return None
            expected += float(outcome.probability) * best

        return expected, bool(distribution.exact)
