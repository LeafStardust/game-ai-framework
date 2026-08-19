from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.the_idol import TheIdolJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(jokers, cards, *, hand=PokerHand.HIGH_CARD, owned_deck=None, owned_known=False):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    if owned_known:
        state.owned_deck = list(owned_deck or [])
    state.jokers = list(jokers)

    return VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_stuntman_projects_current_250_chip_bonus():
    ace = BalatroCard("A", "Spades")

    transition = _project([StuntmanJoker()], [ace])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 266


def test_walkie_talkie_counts_only_scoring_tens_and_fours():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("4", "Hearts"),
    ]

    transition = _project(
        [WalkieTalkieJoker()],
        cards,
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 500


def test_walkie_talkie_retriggers_with_red_seal_scoring_card():
    cards = [
        BalatroCard("10", "Spades", seal="Red"),
        BalatroCard("10", "Hearts"),
    ]

    transition = _project(
        [WalkieTalkieJoker()],
        cards,
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 980


def test_the_idol_resolves_xmult_before_later_additive_mult_card():
    target = BalatroCard("10", "Hearts")
    later_mult = BalatroCard("10", "Clubs", enhancement="Mult")

    transition = _project(
        [TheIdolJoker("10", "Hearts")],
        [target, later_mult],
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 240


def test_the_idol_resolves_after_earlier_additive_mult_card():
    earlier_mult = BalatroCard("10", "Clubs", enhancement="Mult")
    target = BalatroCard("10", "Hearts")

    transition = _project(
        [TheIdolJoker("10", "Hearts")],
        [earlier_mult, target],
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 360


def test_the_idol_accepts_wild_scoring_card_as_target_suit():
    cards = [
        BalatroCard("10", "Spades", enhancement="Wild"),
        BalatroCard("10", "Clubs"),
    ]

    transition = _project(
        [TheIdolJoker("10", "Hearts")],
        cards,
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 120


def test_steel_joker_counts_full_owned_deck_not_remaining_deck():
    ace = BalatroCard("A", "Spades")
    owned = [
        BalatroCard("2", "Clubs", enhancement="Steel"),
        BalatroCard("3", "Diamonds", enhancement="Steel"),
        BalatroCard("4", "Hearts", enhancement="Steel"),
    ]

    transition = _project(
        [SteelJoker()],
        [ace],
        owned_deck=owned,
        owned_known=True,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 25


def test_steel_joker_fails_closed_without_authoritative_owned_deck():
    ace = BalatroCard("A", "Spades")

    transition = _project([SteelJoker()], [ace])

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Steel",)
    assert transition.distribution.minimum == 16
