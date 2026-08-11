from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.card_selector import CardSelector
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _state(cards, *, score, target, hands, discards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = cards
    state.score = score
    state.hands_remaining = hands
    state.discards_remaining = discards
    state.blind = Blind(BlindType.BOSS, target)
    state.jokers = []
    return state


def _choose(state):
    actions = CardSelector().generate_actions(state)
    evaluator = LiveHandDecisionEvaluator()
    scores = [evaluator.evaluate(state, action) for action in actions]
    return GreedyPolicy().select_action(actions, scores)


def test_live_card_chip_scoring_counts_only_pair_cards():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("A", "Clubs"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Spades"),
    ]

    score = BalatroScorer().score(
        PokerHand.PAIR,
        cards=cards,
        include_card_chips=True,
    )

    assert score.chips == 30
    assert score.mult == 2
    assert score.total == 60


def test_live_policy_discards_weak_pair_when_last_hand_cannot_keep_pace():
    state = _state(
        [
            BalatroCard("A", "Spades", live_id=0),
            BalatroCard("Q", "Diamonds", live_id=1),
            BalatroCard("9", "Clubs", live_id=2),
            BalatroCard("10", "Hearts", live_id=3),
            BalatroCard("10", "Clubs", live_id=4),
            BalatroCard("7", "Hearts", live_id=5),
            BalatroCard("5", "Spades", live_id=6),
            BalatroCard("3", "Diamonds", live_id=7),
        ],
        score=364,
        target=600,
        hands=1,
        discards=4,
    )

    action = _choose(state)

    assert action.name == DISCARD_CARDS


def test_live_policy_discards_weak_opening_pair_instead_of_burning_a_hand():
    state = _state(
        [
            BalatroCard("A", "Spades", live_id=0),
            BalatroCard("Q", "Spades", live_id=1),
            BalatroCard("10", "Spades", live_id=2),
            BalatroCard("10", "Diamonds", live_id=3),
            BalatroCard("8", "Spades", live_id=4),
            BalatroCard("6", "Clubs", live_id=5),
            BalatroCard("4", "Clubs", live_id=6),
            BalatroCard("2", "Clubs", live_id=7),
        ],
        score=0,
        target=600,
        hands=4,
        discards=4,
    )

    action = _choose(state)

    assert action.name == DISCARD_CARDS


def test_live_policy_plays_made_flush_that_exceeds_required_pace():
    state = _state(
        [
            BalatroCard("A", "Clubs", live_id=0),
            BalatroCard("10", "Clubs", live_id=1),
            BalatroCard("8", "Clubs", live_id=2),
            BalatroCard("6", "Clubs", live_id=3),
            BalatroCard("2", "Clubs", live_id=4),
            BalatroCard("K", "Hearts", live_id=5),
            BalatroCard("7", "Diamonds", live_id=6),
            BalatroCard("3", "Spades", live_id=7),
        ],
        score=60,
        target=600,
        hands=3,
        discards=4,
    )

    action = _choose(state)

    assert action.name == PLAY_CARDS
    assert HandEvaluator().evaluate(action.cards) == PokerHand.FLUSH


def test_live_policy_plays_pair_immediately_when_it_clears_blind():
    state = _state(
        [
            BalatroCard("10", "Spades", live_id=0),
            BalatroCard("10", "Diamonds", live_id=1),
            BalatroCard("8", "Clubs", live_id=2),
            BalatroCard("6", "Hearts", live_id=3),
            BalatroCard("4", "Spades", live_id=4),
            BalatroCard("3", "Diamonds", live_id=5),
            BalatroCard("2", "Clubs", live_id=6),
            BalatroCard("A", "Hearts", live_id=7),
        ],
        score=550,
        target=600,
        hands=1,
        discards=4,
    )

    action = _choose(state)

    assert action.name == PLAY_CARDS
    assert HandEvaluator().evaluate(action.cards) == PokerHand.PAIR
