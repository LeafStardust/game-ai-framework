from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.scoring import BalatroScorer


def test_jolly_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                JollyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.PAIR,
        state,
        cards
    )

    assert score.chips == 10
    assert score.mult == 10
    assert score.total == 100


def test_zany_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                ZanyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.THREE_OF_A_KIND,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 15
    assert score.total == 450


def test_mad_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                MadJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.TWO_PAIR,
        state,
        cards
    )

    assert score.chips == 20
    assert score.mult == 12
    assert score.total == 240


def test_crazy_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CrazyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("6", "Hearts")
    ]

    score = scorer.score(
        PokerHand.STRAIGHT,
        state,
        cards
    )

    assert score.chips == 30
    assert score.mult == 16
    assert score.total == 480


def test_droll_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                DrollJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.FLUSH,
        state,
        cards
    )

    assert score.chips == 35
    assert score.mult == 14
    assert score.total == 490


def test_flat_mult_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                FlatMultJoker(4)
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 6
    assert score.total == 60


def test_bull_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "money": 15,
            "jokers": [
                BullJoker()
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 8
    assert score.total == 80