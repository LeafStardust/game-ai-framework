import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.dusk import DuskJoker
from games.balatro.jokers.hack import HackJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.seltzer import SeltzerJoker
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers, *, hands_remaining=3):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = hands_remaining
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 10000)
    state.jokers = list(jokers)
    return state


def test_hanging_chad_retriggers_first_scoring_card_chips_and_enhancement():
    card = BalatroCard("K", "Spades", enhancement="Mult")
    state = _state([card], [HangingChadJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    # 5 base Chips + K scored three times = 35 Chips.
    # 1 base Mult + Mult enhancement (+4) three times = 13 Mult.
    assert transition.distribution.minimum == 455
    assert transition.distribution.maximum == 455
    assert transition.joker_projection_complete is True
    assert not hasattr(card, "_projection_extra_retriggers")


def test_hack_retriggers_only_scoring_twos_through_fives():
    two_a = BalatroCard("2", "Spades", enhancement="Mult")
    two_b = BalatroCard("2", "Hearts")
    kicker = BalatroCard("5", "Clubs", enhancement="Mult")
    state = _state([two_a, two_b, kicker], [HackJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        [two_a, two_b, kicker],
    )

    # Only the pair scores. Both 2s retrigger once; the qualifying 5 kicker does not.
    # Chips: 10 + (2 * 2) + (2 * 2) = 18.
    # Mult: 2 + (4 * 2) = 10.
    assert transition.distribution.minimum == 180
    assert transition.joker_projection_complete is True


def test_sock_and_buskin_retriggers_scoring_faces_only():
    king_a = BalatroCard("K", "Spades", enhancement="Glass")
    king_b = BalatroCard("K", "Hearts")
    face_kicker = BalatroCard("Q", "Clubs")
    state = _state([king_a, king_b, face_kicker], [SockAndBuskinJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        [king_a, king_b, face_kicker],
    )

    # Both Kings score twice. The Queen kicker is a face card but does not score.
    # 50 Chips * 2 base Mult * Glass x4 = 400.
    assert transition.distribution.minimum == 400
    assert transition.joker_projection_complete is True


def test_dusk_retriggers_all_scoring_cards_only_on_final_hand():
    cards = [BalatroCard("9", "Spades"), BalatroCard("9", "Hearts")]

    final_state = _state(cards, [DuskJoker()], hands_remaining=1)
    final_transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        final_state,
        cards,
    )
    assert final_transition.distribution.minimum == 92
    assert final_transition.joker_projection_complete is True

    earlier_state = _state(cards, [DuskJoker()], hands_remaining=2)
    earlier_transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        earlier_state,
        cards,
    )
    assert earlier_transition.distribution.minimum == 56
    assert earlier_transition.joker_projection_complete is True


def test_hanging_chad_retriggers_photograph_with_first_scoring_face():
    king = BalatroCard("K", "Spades")
    state = _state([king], [HangingChadJoker(), PhotographJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [king],
    )

    # K scores three times: 5 + 30 = 35 Chips. Photograph's x2 also resolves
    # three times, giving x8 total.
    assert transition.distribution.minimum == 280
    assert transition.distribution.maximum == 280
    assert transition.joker_projection_complete is True


def test_hanging_chad_red_seal_and_seltzer_stack_additively():
    ace = BalatroCard("A", "Spades", seal="Red")
    seltzer = SeltzerJoker()
    seltzer.rounds_remaining = 7
    state = _state([ace], [HangingChadJoker(), seltzer])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # Base trigger + Chad 2 + Seltzer 1 + Red Seal 1 = five Ace triggers.
    assert transition.distribution.minimum == 60
    assert transition.joker_projection_complete is True
    assert seltzer.rounds_remaining == 7
    assert transition.state_after_scoring.jokers[1].rounds_remaining == 6


def test_hanging_chad_expands_lucky_probability_trials():
    ace = BalatroCard("A", "Spades", enhancement="Lucky")
    state = _state([ace], [HangingChadJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.random_sources == ("Lucky mult x3",)
    assert len(transition.distribution.outcomes) == 4
    assert sum(
        outcome.probability
        for outcome in transition.distribution.outcomes
    ) == pytest.approx(1.0)
