import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.onyx_agate import OnyxAgateJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(jokers, cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    return state


def _project(jokers, cards, hand=PokerHand.PAIR):
    transition = VisibleCardScoreOutcomeModel().project_transition(
        hand,
        _state(jokers, cards),
        cards,
    )
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    return transition.distribution.minimum


@pytest.mark.parametrize(
    ("joker", "equivalent_suit"),
    [
        (GreedyJoker(), "Hearts"),
        (LustyJoker(), "Diamonds"),
        (WrathfulJoker(), "Clubs"),
        (GluttonousJoker(), "Spades"),
    ],
)
def test_supported_suit_mult_jokers_respect_smeared_equivalence(
    joker,
    equivalent_suit,
):
    cards = [
        BalatroCard("10", equivalent_suit),
        BalatroCard("10", "Hearts" if equivalent_suit not in {"Hearts", "Diamonds"} else "Clubs"),
    ]

    assert _project([SmearedJoker(), joker], cards) == 150


def test_ancient_respects_smeared_equivalent_suit():
    ancient = AncientJoker()
    ancient.suit = "Hearts"
    cards = [BalatroCard("10", "Diamonds"), BalatroCard("10", "Clubs")]

    assert _project([SmearedJoker(), ancient], cards) == 90


def test_arrowhead_scores_smeared_spade_equivalent_card():
    cards = [BalatroCard("10", "Clubs"), BalatroCard("10", "Hearts")]

    assert _project([SmearedJoker(), ArrowheadJoker()], cards) == 160


def test_arrowhead_retriggers_with_red_seal_scoring_card():
    cards = [
        BalatroCard("10", "Spades", seal="Red"),
        BalatroCard("10", "Hearts"),
    ]

    # Pair base 10 Chips; the sealed Spade scores twice and contributes
    # Arrowhead's +50 twice, then the Heart scores once: 140 Chips * 2 Mult.
    assert _project([ArrowheadJoker()], cards) == 280


def test_onyx_agate_scores_smeared_club_equivalent_card():
    cards = [BalatroCard("10", "Spades"), BalatroCard("10", "Hearts")]

    assert _project([SmearedJoker(), OnyxAgateJoker()], cards) == 270


def test_seeing_double_requires_two_distinct_scoring_cards():
    cards = [
        BalatroCard("10", "Hearts"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("2", "Clubs"),
    ]

    # The Club is only a non-scoring kicker for the Pair.
    assert _project([SeeingDoubleJoker()], cards) == 60


def test_seeing_double_activates_for_scoring_club_and_other_suit():
    cards = [BalatroCard("10", "Clubs"), BalatroCard("10", "Hearts")]

    assert _project([SeeingDoubleJoker()], cards) == 120


def test_seeing_double_accepts_wild_as_club_with_second_scoring_card():
    cards = [
        BalatroCard("10", "Hearts", enhancement="Wild"),
        BalatroCard("10", "Hearts"),
    ]

    assert _project([SeeingDoubleJoker()], cards) == 120


def test_seeing_double_respects_smeared_black_suit_equivalence():
    cards = [BalatroCard("10", "Clubs"), BalatroCard("10", "Clubs")]

    assert _project([SmearedJoker(), SeeingDoubleJoker()], cards) == 120
