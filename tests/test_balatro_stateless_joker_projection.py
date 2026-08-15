import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.wily_joker import WilyJoker
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
