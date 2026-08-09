from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.half_joker import HalfJoker


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


def test_sly_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                SlyJoker()
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

    assert score.chips == 60
    assert score.mult == 2
    assert score.total == 120


def test_wily_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                WilyJoker()
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

    assert score.chips == 130
    assert score.mult == 3
    assert score.total == 390


def test_clever_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CleverJoker()
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

    assert score.chips == 100
    assert score.mult == 2
    assert score.total == 200


def test_devious_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                DeviousJoker()
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

    assert score.chips == 130
    assert score.mult == 4
    assert score.total == 520


def test_crafty_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                CraftyJoker()
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

    assert score.chips == 115
    assert score.mult == 4
    assert score.total == 460


def test_greedy_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                GreedyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Diamonds"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_lusty_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                LustyJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_wrathful_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                WrathfulJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("7", "Spades"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Clubs"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_gluttonous_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                GluttonousJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Clubs"),
        BalatroCard("7", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Spades")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 7
    assert score.total == 35


def test_even_steven_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                EvenStevenJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("K", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 9
    assert score.total == 45


def test_odd_todd_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                OddToddJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 98
    assert score.mult == 1
    assert score.total == 98


def test_fibonacci_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                FibonacciJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("2", "Spades"),
        BalatroCard("5", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("Q", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 25
    assert score.total == 125


def test_scholar_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                ScholarJoker()
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

    assert score.chips == 50
    assert score.mult == 10
    assert score.total == 500


def test_half_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                HalfJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Clubs")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 21
    assert score.total == 105


def test_half_joker_does_not_trigger_above_three_cards():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                HalfJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Diamonds")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 5
    assert score.mult == 1
    assert score.total == 5


def test_banner_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "discards_remaining": 3,
            "jokers": [
                BannerJoker()
            ]
        }
    )()

    cards = [
        BalatroCard("A", "Hearts")
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards
    )

    assert score.chips == 95
    assert score.mult == 1
    assert score.total == 95