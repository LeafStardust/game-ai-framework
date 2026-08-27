from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from framework.core.action import Action
from framework.decision.evaluator import Evaluator

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.card_selector import CardSelector
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.scoring import BalatroScorer
from games.balatro.live.final_joker_outcomes import (
    LiveFinalJokerScoreOutcomeModel,
)
from games.balatro.live.score_outcomes import ScoreOutcome


@dataclass(frozen=True)
class LivePlayProjection:
    hand: PokerHand
    hand_score: int
    expected_hand_score: float
    maximum_hand_score: int
    current_score: int
    projected_total: int
    expected_projected_total: float
    maximum_projected_total: int
    blind_target: int
    remaining_before: int
    remaining_after: int
    clears_blind: bool
    clear_probability: float
    outcomes: tuple[ScoreOutcome, ...]
    state_after_scoring: object | None = None
    joker_projection_complete: bool = True
    unsupported_jokers: tuple[str, ...] = ()
    random_sources: tuple[str, ...] = ()

    @property
    def deterministic(self) -> bool:
        return len(self.outcomes) == 1

    @property
    def possible_clear(self) -> bool:
        return self.clear_probability > 0.0


@dataclass(frozen=True)
class _DecisionContext:
    remaining_chips: float
    required_per_hand: float
    best_play_score: float
    best_play_hand: PokerHand


class LiveHandDecisionEvaluator(Evaluator):
    """Pace-aware evaluator for live play/discard decisions.

    It deliberately uses only currently visible state. Remaining deck order is not
    consulted. Validated Jokers are projected on deep branch copies so stateful
    effects cannot mutate the authoritative live state. Unsupported Joker semantics
    are surfaced explicitly for the caller to guard before real execution.

    Visible-card randomness is never sampled during decision-making. The score
    outcome model supplies a guaranteed floor, expectation, maximum and discrete
    clear probability instead.
    """

    STRONG_MADE_HANDS = {
        PokerHand.STRAIGHT,
        PokerHand.FLUSH,
        PokerHand.FULL_HOUSE,
        PokerHand.FOUR_OF_A_KIND,
        PokerHand.STRAIGHT_FLUSH,
    }

    RANK_ORDER = {
        "A": 14,
        "K": 13,
        "Q": 12,
        "J": 11,
        "10": 10,
        "9": 9,
        "8": 8,
        "7": 7,
        "6": 6,
        "5": 5,
        "4": 4,
        "3": 3,
        "2": 2,
    }

    # Suit-debuff bosses preserve rank/suit identity for poker construction, but the
    # debuffed cards contribute no card chips, enhancement/edition effects, or held
    # effects. Keep that fact as bounded recovery evidence inside the canonical D1
    # evaluator rather than installing a late monkeypatch around `_discard_value`.
    DISCARDED_DEBUFFED_CARD_BONUS = 12.0
    RETAINED_DEBUFFED_CARD_PENALTY = 4.0

    # A discard always spends exactly one discard resource whether it redraws one
    # card or five. When the current best play is materially below pace and there is
    # another discard available, a wider redraw therefore has literal recovery
    # value. This used to live in the final Red/White correction layer; it belongs in
    # the canonical D1 evaluator so candidate generation and arbitration share it.
    REDRAW_EFFICIENCY_BASE = 8.0
    REDRAW_EFFICIENCY_SHORTFALL_WEIGHT = 8.0

    def __init__(self):
        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()
        self.score_outcomes = LiveFinalJokerScoreOutcomeModel(self.scorer)
        self.action_generator = CardSelector()
        self._cached_state_id: int | None = None
        self._cached_context: _DecisionContext | None = None
        self._outer_d1_cache_state_id: int | None = None
        self._outer_d1_projection_cache: dict[tuple[str, tuple[int, ...]], LivePlayProjection] = {}
        self._outer_d1_evaluation_cache: dict[tuple[str, tuple[int, ...]], float] = {}
        self._outer_d1_guaranteed_clear_cached = False
        self._outer_d1_guaranteed_clear_value = False

    @staticmethod
    def _action_key(action) -> tuple[str, tuple[int, ...]]:
        cards = tuple(getattr(action, "cards", ()) or ())
        return (
            str(getattr(action, "name", "")),
            tuple(id(card) for card in cards),
        )

    def _ensure_outer_d1_cache(self, state) -> None:
        state_id = id(state)
        if self._outer_d1_cache_state_id == state_id:
            return
        self._outer_d1_cache_state_id = state_id
        self._outer_d1_projection_cache = {}
        self._outer_d1_evaluation_cache = {}
        self._outer_d1_guaranteed_clear_cached = False
        self._outer_d1_guaranteed_clear_value = False

    def evaluate(self, state, action: Action) -> float:
        self._ensure_outer_d1_cache(state)
        key = self._action_key(action)
        cached = self._outer_d1_evaluation_cache.get(key)
        if cached is not None:
            return cached

        context = self._context(state)

        if action.name == PLAY_CARDS:
            value = self._play_value(state, action, context)
        elif action.name == DISCARD_CARDS:
            value = self._discard_value(state, action, context)
        else:
            value = -1_000_000.0

        self._outer_d1_evaluation_cache[key] = value
        return value

    def project_play(self, state, action: Action) -> LivePlayProjection:
        if action.name != PLAY_CARDS:
            raise ValueError("live play projection requires PLAY_CARDS")
        if not action.cards:
            raise ValueError("live play projection requires at least one played card")

        self._ensure_outer_d1_cache(state)
        key = self._action_key(action)
        cached = self._outer_d1_projection_cache.get(key)
        if cached is not None:
            return cached

        hand = self._hand_for_cards(state, action.cards)
        transition = self.score_outcomes.project_transition(
            hand,
            state,
            action.cards,
            include_card_chips=True,
        )
        distribution = transition.distribution
        current_score = int(getattr(state, "score", 0))
        target = int(getattr(getattr(state, "blind", None), "requirement", 0))
        remaining_before = max(0, target - current_score)
        projected_total = current_score + distribution.minimum
        expected_projected_total = current_score + distribution.expected
        maximum_projected_total = current_score + distribution.maximum
        remaining_after = max(0, target - projected_total)

        if target <= 0 or remaining_before <= 0:
            clear_probability = 1.0 if target > 0 else 0.0
        else:
            clear_probability = distribution.probability_at_least(remaining_before)

        projection = LivePlayProjection(
            hand=hand,
            hand_score=distribution.minimum,
            expected_hand_score=distribution.expected,
            maximum_hand_score=distribution.maximum,
            current_score=current_score,
            projected_total=projected_total,
            expected_projected_total=expected_projected_total,
            maximum_projected_total=maximum_projected_total,
            blind_target=target,
            remaining_before=remaining_before,
            remaining_after=remaining_after,
            clears_blind=(
                target > 0
                and remaining_before > 0
                and distribution.minimum >= remaining_before
            ),
            clear_probability=clear_probability,
            outcomes=distribution.outcomes,
            state_after_scoring=transition.state_after_scoring,
            joker_projection_complete=transition.joker_projection_complete,
            unsupported_jokers=transition.unsupported_jokers,
            random_sources=distribution.random_sources,
        )
        self._outer_d1_projection_cache[key] = projection
        return projection

    def _context(self, state) -> _DecisionContext:
        state_id = id(state)
        if self._cached_state_id == state_id and self._cached_context is not None:
            return self._cached_context

        requirement = int(getattr(getattr(state, "blind", None), "requirement", 0))
        remaining = max(1.0, float(requirement - getattr(state, "score", 0)))
        hands = max(1, int(getattr(state, "hands_remaining", 1)))
        required_per_hand = remaining / hands

        best_score = 0.0
        best_hand = PokerHand.HIGH_CARD
        for play in self.action_generator.generate_play_actions(state):
            estimate = self._estimate_play(state, play)
            if estimate > best_score:
                best_score = estimate
                best_hand = self._hand_for_cards(state, play.cards)

        context = _DecisionContext(
            remaining_chips=remaining,
            required_per_hand=max(1.0, required_per_hand),
            best_play_score=best_score,
            best_play_hand=best_hand,
        )
        self._cached_state_id = state_id
        self._cached_context = context
        return context

    def _play_value(self, state, action, context: _DecisionContext) -> float:
        projection = self.project_play(state, action)
        estimate = projection.expected_hand_score
        hand = projection.hand

        if projection.clears_blind:
            return 2_000.0 + projection.hand_score

        probabilistic_clear_bonus = 0.0
        if projection.clear_probability > 0.0:
            probabilistic_clear_bonus = 500.0 * projection.clear_probability

        progress = (estimate / context.remaining_chips) * 100.0
        progress += probabilistic_clear_bonus
        pace_ratio = estimate / context.required_per_hand

        if hand in self.STRONG_MADE_HANDS:
            progress += 35.0
        elif hand in {PokerHand.THREE_OF_A_KIND, PokerHand.TWO_PAIR}:
            progress += 15.0
        elif hand == PokerHand.PAIR:
            progress += 5.0

        discards = int(getattr(state, "discards_remaining", 0))
        hands = max(1, int(getattr(state, "hands_remaining", 1)))
        if discards > 0 and pace_ratio < 1.0:
            shortfall = 1.0 - pace_ratio
            progress -= shortfall * 50.0
            progress -= max(0, 4 - hands) * 10.0

        return progress

    def _discard_value(self, state, action, context: _DecisionContext) -> float:
        if int(getattr(state, "discards_remaining", 0)) <= 0:
            return -1_000_000.0

        if self._has_guaranteed_clearing_play(state):
            return -2_000.0

        kept_cards = self._kept_cards(state.hand, action.cards)
        promise = self._retained_structure_value(kept_cards)

        pace_ratio = context.best_play_score / context.required_per_hand
        shortfall = max(0.0, 1.0 - pace_ratio)
        hands = max(1, int(getattr(state, "hands_remaining", 1)))

        value = 40.0
        value += shortfall * 50.0
        value += max(0, 4 - hands) * 10.0
        value += promise
        value += min(5, len(action.cards)) * 4.0

        if context.best_play_hand in self.STRONG_MADE_HANDS:
            value -= 250.0
        elif pace_ratio >= 1.0:
            value -= 80.0

        discards_remaining = int(getattr(state, "discards_remaining", 0))
        if discards_remaining <= 1:
            value -= 10.0

        redraws = len(tuple(getattr(action, "cards", ()) or ()))
        if shortfall > 0.0 and redraws > 1 and discards_remaining > 1:
            extra_redraws = min(4, redraws - 1)
            value += extra_redraws * (
                self.REDRAW_EFFICIENCY_BASE
                + self.REDRAW_EFFICIENCY_SHORTFALL_WEIGHT * shortfall
            )

        hand = tuple(getattr(state, "hand", ()) or ())
        if hand and any(self.scorer.is_card_debuffed(card) for card in hand):
            discarded = tuple(getattr(action, "cards", ()) or ())
            discarded_ids = {id(card) for card in discarded}
            discarded_debuffed = sum(
                1 for card in discarded if self.scorer.is_card_debuffed(card)
            )
            retained_debuffed = sum(
                1
                for card in hand
                if id(card) not in discarded_ids and self.scorer.is_card_debuffed(card)
            )
            value += discarded_debuffed * self.DISCARDED_DEBUFFED_CARD_BONUS
            value -= retained_debuffed * self.RETAINED_DEBUFFED_CARD_PENALTY

        return value

    def _estimate_play(self, state, action) -> float:
        hand = self._hand_for_cards(state, action.cards)
        return self.score_outcomes.project(
            hand,
            state,
            action.cards,
            include_card_chips=True,
        ).expected

    def _has_guaranteed_clearing_play(self, state) -> bool:
        self._ensure_outer_d1_cache(state)
        if self._outer_d1_guaranteed_clear_cached:
            return self._outer_d1_guaranteed_clear_value

        remaining = max(
            0,
            int(getattr(getattr(state, "blind", None), "requirement", 0))
            - int(getattr(state, "score", 0)),
        )
        if remaining <= 0:
            result = True
        else:
            result = False
            for play in self.action_generator.generate_play_actions(state):
                hand = self._hand_for_cards(state, play.cards)
                distribution = self.score_outcomes.project(
                    hand,
                    state,
                    play.cards,
                    include_card_chips=True,
                )
                if distribution.minimum >= remaining:
                    result = True
                    break

        self._outer_d1_guaranteed_clear_value = bool(result)
        self._outer_d1_guaranteed_clear_cached = True
        return self._outer_d1_guaranteed_clear_value

    def _hand_for_cards(self, state, cards) -> PokerHand:
        return self.hand_evaluator.evaluate(
            list(cards or []),
            rules=hand_rules_for_state(state),
        )

    @staticmethod
    def _kept_cards(hand, discarded) -> list:
        discarded_ids = {id(card) for card in discarded}
        return [card for card in hand if id(card) not in discarded_ids]

    def _retained_structure_value(self, cards) -> float:
        if not cards:
            return 0.0

        regular = [
            card
            for card in cards
            if getattr(card, "enhancement", None) != "Stone"
        ]
        if not regular:
            return 0.0

        ranks = [str(card.rank) for card in regular]
        rank_counts = Counter(ranks)
        counts = sorted(rank_counts.values(), reverse=True)

        value = 0.0
        if counts and counts[0] >= 4:
            value += 90.0
        elif counts and counts[0] == 3:
            value += 60.0
        elif counts and counts[0] == 2:
            value += 35.0

        if sum(1 for count in counts if count >= 2) >= 2:
            value += 20.0

        suit_counts = Counter(str(card.suit) for card in regular)
        max_suit = max(suit_counts.values(), default=0)
        if max_suit >= 4:
            value += 50.0
        elif max_suit == 3:
            value += 25.0
        elif max_suit == 2:
            value += 8.0

        run = self._longest_straight_run(ranks)
        if run >= 4:
            value += 45.0
        elif run == 3:
            value += 20.0

        high_cards = sorted(
            (self.scorer.card_chip_value(card) for card in regular),
            reverse=True,
        )[:2]
        value += sum(high_cards) * 0.5
        return value

    def _longest_straight_run(self, ranks) -> int:
        values = {
            self.RANK_ORDER[rank]
            for rank in ranks
            if rank in self.RANK_ORDER
        }
        if 14 in values:
            values.add(1)
        if not values:
            return 0

        longest = 1
        current = 1
        ordered = sorted(values)
        for previous, value in zip(ordered, ordered[1:]):
            if value == previous + 1:
                current += 1
                longest = max(longest, current)
            elif value != previous:
                current = 1
        return longest
