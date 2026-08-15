import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.triboulet import TribouletJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, joker):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.blind = Blind(BlindType.BIG, 1000)
    state.jokers = [joker]
    return state


@pytest.mark.parametrize(
    ("joker", "hand", "cards", "expected"),
    [
        (
            BannerJoker(),
            PokerHand.HIGH_CARD,
            [BalatroCard("A", "Spades")],
            76,
        ),
        (
            HalfJoker(),
            PokerHand.HIGH_CARD,
            [BalatroCard("A", "Spades")],
            336,
        ),
        (
            SlyJoker(),
            PokerHand.PAIR,
            [BalatroCard("10", "Spades"), BalatroCard("10", "Diamonds")],
            160,
        ),
        (
            WilyJoker(),
            PokerHand.THREE_OF_A_KIND,
            [
                BalatroCard("9", "Spades"),
                BalatroCard("9", "Diamonds"),
                BalatroCard("9", "Clubs"),
            ],
            471,
        ),
        (
            CleverJoker(),
            PokerHand.TWO_PAIR,
            [
                BalatroCard("8", "Spades"),
                BalatroCard("8", "Diamonds"),
                BalatroCard("7", "Clubs"),
                BalatroCard("7", "Hearts"),
            ],
            260,
        ),
        (
            CraftyJoker(),
            PokerHand.FLUSH,
            [
                BalatroCard("2", "Hearts"),
                BalatroCard("4", "Hearts"),
                BalatroCard("6", "Hearts"),
                BalatroCard("8", "Hearts"),
                BalatroCard("10", "Hearts"),
            ],
            580,
        ),
        (
            DrollJoker(),
            PokerHand.FLUSH,
            [
                BalatroCard("2", "Hearts"),
                BalatroCard("4", "Hearts"),
                BalatroCard("6", "Hearts"),
                BalatroCard("8", "Hearts"),
                BalatroCard("10", "Hearts"),
            ],
            910,
        ),
    ],
)
def test_exact_stateless_score_jokers_are_admitted(joker, hand, cards, expected):
    state = _state(cards, joker)

    transition = VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )

    assert transition.distribution.minimum == expected
    assert transition.distribution.maximum == expected
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert state.jokers[0] is joker
    assert transition.state_after_scoring.jokers[0] is not joker


@pytest.mark.parametrize(
    ("joker", "cards", "expected"),
    [
        (
            GreedyJoker(),
            [
                BalatroCard("10", "Diamonds"),
                BalatroCard("10", "Spades"),
                BalatroCard("2", "Diamonds"),
            ],
            150,
        ),
        (
            LustyJoker(),
            [
                BalatroCard("10", "Hearts"),
                BalatroCard("10", "Spades"),
                BalatroCard("2", "Hearts"),
            ],
            150,
        ),
        (
            WrathfulJoker(),
            [
                BalatroCard("10", "Spades"),
                BalatroCard("10", "Hearts"),
                BalatroCard("2", "Spades"),
            ],
            150,
        ),
        (
            GluttonousJoker(),
            [
                BalatroCard("10", "Clubs"),
                BalatroCard("10", "Hearts"),
                BalatroCard("2", "Clubs"),
            ],
            150,
        ),
        (
            FibonacciJoker(),
            [
                BalatroCard("10", "Spades"),
                BalatroCard("10", "Hearts"),
                BalatroCard("A", "Diamonds"),
            ],
            60,
        ),
        (
            EvenStevenJoker(),
            [
                BalatroCard("10", "Spades"),
                BalatroCard("10", "Hearts"),
                BalatroCard("8", "Diamonds"),
            ],
            300,
        ),
        (
            OddToddJoker(),
            [
                BalatroCard("9", "Spades"),
                BalatroCard("9", "Hearts"),
                BalatroCard("A", "Diamonds"),
            ],
            180,
        ),
    ],
)
def test_played_card_jokers_ignore_non_scoring_kickers(joker, cards, expected):
    state = _state(cards, joker)

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == expected
    assert transition.distribution.maximum == expected
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()


def test_photograph_uses_first_scoring_card_not_first_played_card():
    cards = [
        BalatroCard("2", "Diamonds"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Spades"),
    ]
    state = _state(cards, PhotographJoker())

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 120
    assert transition.distribution.maximum == 120
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()


@pytest.mark.parametrize(
    ("joker", "cards", "expected"),
    [
        (
            ScaryFaceJoker(),
            [
                BalatroCard("K", "Hearts"),
                BalatroCard("K", "Spades"),
                BalatroCard("Q", "Diamonds"),
            ],
            180,
        ),
        (
            SmileyFaceJoker(),
            [
                BalatroCard("K", "Hearts"),
                BalatroCard("K", "Spades"),
                BalatroCard("Q", "Diamonds"),
            ],
            360,
        ),
        (
            TribouletJoker(),
            [
                BalatroCard("K", "Hearts"),
                BalatroCard("K", "Spades"),
                BalatroCard("Q", "Diamonds"),
            ],
            240,
        ),
        (
            ScholarJoker(),
            [
                BalatroCard("10", "Hearts"),
                BalatroCard("10", "Spades"),
                BalatroCard("A", "Diamonds"),
            ],
            60,
        ),
    ],
)
def test_face_and_rank_jokers_ignore_non_scoring_kickers(joker, cards, expected):
    state = _state(cards, joker)

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == expected
    assert transition.distribution.maximum == expected
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
