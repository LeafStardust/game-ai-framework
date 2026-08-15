import pytest

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.blind = Blind(BlindType.BIG, 10000)
    state.jokers = list(jokers)
    return state


def _project(cards, jokers):
    state = _state(cards, jokers)
    action = BalatroAction(PLAY_CARDS, cards=list(cards))
    return LiveHandDecisionEvaluator().project_play(state, action)


def test_four_fingers_recognizes_and_scores_four_card_straight():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
    ]

    projection = _project(cards, [FourFingersJoker()])

    assert projection.hand == PokerHand.STRAIGHT
    assert projection.hand_score == 176
    assert projection.joker_projection_complete is True


def test_four_fingers_straight_flush_can_use_different_four_card_subsets():
    cards = [
        BalatroCard("2", "Spades"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("5", "Spades"),
        BalatroCard("10", "Spades"),
    ]

    projection = _project(cards, [FourFingersJoker()])

    assert projection.hand == PokerHand.STRAIGHT_FLUSH
    # Straight subset: 2,3,4,5. Flush subset: 2,3,5,10. Their union scores.
    assert projection.hand_score == 992
    assert projection.joker_projection_complete is True


def test_shortcut_recognizes_one_rank_gaps():
    cards = [
        BalatroCard("10", "Hearts"),
        BalatroCard("8", "Spades"),
        BalatroCard("6", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Hearts"),
    ]

    projection = _project(cards, [ShortcutJoker()])

    assert projection.hand == PokerHand.STRAIGHT
    assert projection.hand_score == 248
    assert projection.joker_projection_complete is True


def test_four_fingers_and_shortcut_combine_for_straight_flush():
    cards = [
        BalatroCard("Q", "Spades"),
        BalatroCard("J", "Spades"),
        BalatroCard("9", "Hearts"),
        BalatroCard("7", "Spades"),
        BalatroCard("3", "Spades"),
    ]

    projection = _project(cards, [FourFingersJoker(), ShortcutJoker()])

    assert projection.hand == PokerHand.STRAIGHT_FLUSH
    assert projection.hand_score == 1112
    assert projection.joker_projection_complete is True


def test_splash_scores_kicker_and_its_on_scored_joker_effect():
    cards = [
        BalatroCard("10", "Diamonds"),
        BalatroCard("10", "Spades"),
        BalatroCard("A", "Clubs"),
    ]

    projection = _project(cards, [SplashJoker(), FibonacciJoker()])

    assert projection.hand == PokerHand.PAIR
    # 41 Chips; base 2 Mult + Fibonacci +8 from the scoring Ace.
    assert projection.hand_score == 410
    assert projection.joker_projection_complete is True


def test_splash_includes_non_hand_lucky_card_in_probability_model():
    cards = [
        BalatroCard("10", "Diamonds"),
        BalatroCard("10", "Spades"),
        BalatroCard("A", "Clubs", enhancement="Lucky"),
    ]
    state = _state(cards, [SplashJoker()])

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert distribution.random_sources == ("Lucky mult x1",)
    assert distribution.minimum == 82
    assert distribution.maximum == 902
    assert len(distribution.outcomes) == 2
    assert sum(outcome.probability for outcome in distribution.outcomes) == pytest.approx(1.0)


def test_without_splash_pair_kicker_still_does_not_score():
    cards = [
        BalatroCard("10", "Diamonds"),
        BalatroCard("10", "Spades"),
        BalatroCard("A", "Clubs"),
    ]
    state = _state(cards, [])

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert distribution.minimum == 60
    assert distribution.maximum == 60
