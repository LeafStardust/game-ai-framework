from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.shoot_the_moon import ShootTheMoonJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(hand, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(hand)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 10000)
    state.jokers = list(jokers)
    return state


def test_mime_retriggers_steel_card_held_in_hand():
    played = BalatroCard("K", "Clubs")
    steel = BalatroCard("2", "Spades", enhancement="Steel")
    state = _state([played, steel], [MimeJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # 15 Chips * (1 * 1.5 * 1.5) Mult.
    assert transition.distribution.minimum == 33
    assert transition.distribution.maximum == 33
    assert transition.joker_projection_complete is True


def test_mime_retriggers_baron_on_held_king():
    played = BalatroCard("2", "Clubs")
    king = BalatroCard("K", "Spades")
    state = _state([played, king], [BaronJoker(), MimeJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # 7 Chips * (1 * 1.5 * 1.5) Mult.
    assert transition.distribution.minimum == 15
    assert transition.distribution.maximum == 15
    assert transition.joker_projection_complete is True


def test_mime_preserves_held_card_order_for_shoot_the_moon_then_steel():
    played = BalatroCard("K", "Clubs")
    queen = BalatroCard("Q", "Hearts")
    steel = BalatroCard("2", "Spades", enhancement="Steel")
    state = _state(
        [played, queen, steel],
        [ShootTheMoonJoker(), MimeJoker()],
    )

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # Queen: +13 twice => Mult 27. Steel: x1.5 twice => 60.75.
    # 15 Chips * 60.75 = 911.25, truncated to 911.
    assert transition.distribution.minimum == 911
    assert transition.distribution.maximum == 911
    assert transition.joker_projection_complete is True


def test_mime_preserves_held_card_order_for_steel_then_shoot_the_moon():
    played = BalatroCard("K", "Clubs")
    steel = BalatroCard("2", "Spades", enhancement="Steel")
    queen = BalatroCard("Q", "Hearts")
    state = _state(
        [played, steel, queen],
        [ShootTheMoonJoker(), MimeJoker()],
    )

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # Steel first: Mult 1 -> 2.25. Queen then adds +26 => 28.25.
    # 15 Chips * 28.25 = 423.75, truncated to 423.
    assert transition.distribution.minimum == 423
    assert transition.distribution.maximum == 423
    assert transition.joker_projection_complete is True


def test_mime_retriggers_raised_fist_lowest_held_card():
    played = BalatroCard("K", "Clubs")
    lowest = BalatroCard("2", "Hearts")
    other = BalatroCard("9", "Spades")
    state = _state(
        [played, lowest, other],
        [RaisedFistJoker(), MimeJoker()],
    )

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # Base Mult 1 + (2 * rank 2) twice = 9 Mult; 15 Chips * 9.
    assert transition.distribution.minimum == 135
    assert transition.distribution.maximum == 135
    assert transition.joker_projection_complete is True


def test_red_seal_and_mime_stack_on_held_steel_king_with_baron():
    played = BalatroCard("2", "Clubs")
    king = BalatroCard(
        "K",
        "Spades",
        enhancement="Steel",
        seal="Red",
    )
    state = _state([played, king], [BaronJoker(), MimeJoker()])

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    # Held King activates three times: base + Red Seal + Mime.
    # Each activation gives Steel x1.5 and Baron x1.5 => six x1.5 factors.
    assert transition.distribution.minimum == 79
    assert transition.distribution.maximum == 79
    assert transition.joker_projection_complete is True


def test_debuffed_held_card_does_not_trigger_mime_or_on_held_jokers():
    played = BalatroCard("K", "Clubs")
    queen = BalatroCard("Q", "Hearts", enhancement="Steel", debuffed=True)
    state = _state(
        [played, queen],
        [ShootTheMoonJoker(), MimeJoker()],
    )

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
    )

    assert transition.distribution.minimum == 15
    assert transition.distribution.maximum == 15
    assert transition.joker_projection_complete is True
