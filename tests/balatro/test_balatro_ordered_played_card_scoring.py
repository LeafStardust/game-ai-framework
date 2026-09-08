from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.wee_joker import WeeJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers=()):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 10000)
    state.jokers = list(jokers)
    return state


def test_glass_before_later_mult_card_preserves_scoring_card_order():
    cards = [
        BalatroCard("5", "Hearts", enhancement="Glass"),
        BalatroCard("6", "Hearts", enhancement="Mult"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
        BalatroCard("9", "Hearts"),
    ]
    state = _state(cards)

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.FLUSH,
        state,
        cards,
    )

    # Base Mult 4 -> Glass x2 = 8 -> later Mult card +4 = 12.
    # Base 35 Chips + card ranks 35 = 70 Chips; 70 * 12 = 840.
    assert transition.distribution.minimum == 840
    assert transition.distribution.maximum == 840


def test_photograph_targets_first_scoring_face_after_earlier_nonface():
    cards = [
        BalatroCard("10", "Hearts", enhancement="Mult"),
        BalatroCard("K", "Hearts"),
        BalatroCard("8", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("6", "Hearts"),
    ]
    state = _state(cards, [PhotographJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.FLUSH,
        state,
        cards,
    )

    # The 10 scores first and raises Mult 4 -> 8. Photograph waits for the King,
    # then doubles 8 -> 16. Chips are 35 + 41 = 76; 76 * 16 = 1216.
    assert transition.distribution.minimum == 1216
    assert transition.distribution.maximum == 1216
    assert transition.joker_projection_complete is True


def test_on_scored_jokers_resolve_left_to_right_for_each_card():
    card = BalatroCard("K", "Hearts")

    photo_first = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        _state([card], [PhotographJoker(), LustyJoker()]),
        [card],
    )
    lusty_first = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        _state([card], [LustyJoker(), PhotographJoker()]),
        [card],
    )

    # 15 Chips. Photograph then Lusty: (1 * 2) + 3 = 5 Mult => 75.
    # Lusty then Photograph: (1 + 3) * 2 = 8 Mult => 120.
    assert photo_first.distribution.minimum == 75
    assert lusty_first.distribution.minimum == 120


def test_hanging_chad_retriggers_ordered_photograph_activation():
    card = BalatroCard("K", "Spades")
    state = _state([card], [HangingChadJoker(), PhotographJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    # K scores three times: 5 + 30 = 35 Chips. Photograph x2 resolves on each
    # activation of the target face card: 1 -> 2 -> 4 -> 8 Mult.
    assert transition.distribution.minimum == 280
    assert transition.distribution.maximum == 280


def test_hanging_chad_retriggers_wee_growth_but_wee_pays_once_per_hand():
    card = BalatroCard("2", "Spades")
    wee = WeeJoker()
    state = _state([card], [HangingChadJoker(), wee])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    # Base 5 Chips + the 2 scoring three times = 11 Chips. Wee grows by 8 on
    # each activation (24 total), then contributes its final 24 Chips once.
    assert transition.distribution.minimum == 35
    assert transition.distribution.maximum == 35
    assert wee.chips == 0
    assert transition.state_after_scoring.jokers[1].chips == 24
