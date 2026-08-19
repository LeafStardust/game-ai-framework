from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.joker_stencil import JokerStencil
from games.balatro.jokers.stone_joker import StoneJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(
    joker,
    *,
    held=None,
    deck=None,
    owned_deck=None,
    owned_deck_known=False,
    joker_slots=5,
    extra_jokers=None,
):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace, *list(held or [])]
    state.deck = list(deck or [])
    if owned_deck_known:
        state.owned_deck = list(owned_deck or [])
    state.joker_slots = joker_slots
    state.jokers = [joker, *list(extra_jokers or [])]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )
    return transition


def test_blackboard_triggers_with_no_cards_left_held_in_hand():
    transition = _project(BlackboardJoker())

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 48


def test_blackboard_accepts_held_wild_card_as_black_suit():
    wild = BalatroCard("2", "Hearts", enhancement="Wild")

    transition = _project(BlackboardJoker(), held=[wild])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 48


def test_blackboard_rejects_held_stone_or_red_card():
    stone = BalatroCard("2", "Spades", enhancement="Stone")
    heart = BalatroCard("3", "Hearts")

    stone_transition = _project(BlackboardJoker(), held=[stone])
    red_transition = _project(BlackboardJoker(), held=[heart])

    assert stone_transition.distribution.minimum == 16
    assert red_transition.distribution.minimum == 16


def test_drivers_license_uses_authoritative_owned_deck_threshold():
    enhanced = [
        BalatroCard("2", "Clubs", enhancement="Bonus")
        for _ in range(16)
    ]
    remaining = [BalatroCard("3", "Hearts")]

    active = _project(
        DriversLicenseJoker(),
        deck=remaining,
        owned_deck=enhanced,
        owned_deck_known=True,
    )
    inactive = _project(
        DriversLicenseJoker(),
        deck=enhanced,
        owned_deck=enhanced[:15],
        owned_deck_known=True,
    )

    assert active.joker_projection_complete is True
    assert active.distribution.minimum == 48
    assert inactive.joker_projection_complete is True
    assert inactive.distribution.minimum == 16


def test_drivers_license_fails_closed_without_owned_deck():
    enhanced_remaining = [
        BalatroCard("2", "Clubs", enhancement="Bonus")
        for _ in range(16)
    ]

    transition = _project(
        DriversLicenseJoker(),
        deck=enhanced_remaining,
    )

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("DriversLicense",)
    assert transition.distribution.minimum == 16


def test_stone_joker_counts_stones_in_owned_deck_not_remaining_deck():
    owned = [
        BalatroCard("2", "Clubs", enhancement="Stone"),
        BalatroCard("3", "Diamonds", enhancement="Stone"),
        BalatroCard("4", "Hearts", enhancement="Stone"),
    ]
    remaining = [
        BalatroCard("5", "Spades", enhancement="Stone")
        for _ in range(8)
    ]

    transition = _project(
        StoneJoker(),
        deck=remaining,
        owned_deck=owned,
        owned_deck_known=True,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 91


def test_stone_joker_fails_closed_without_owned_deck():
    transition = _project(
        StoneJoker(),
        deck=[BalatroCard("2", "Clubs", enhancement="Stone")],
    )

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Stone",)
    assert transition.distribution.minimum == 16


def test_single_joker_stencil_counts_itself_as_empty_slot():
    transition = _project(JokerStencil(), joker_slots=5)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 80


def test_multiple_joker_stencils_each_count_all_stencils_as_empty():
    transition = _project(
        JokerStencil(),
        joker_slots=5,
        extra_jokers=[JokerStencil()],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 400


def test_non_stencil_joker_consumes_one_stencil_slot():
    transition = _project(
        JokerStencil(),
        joker_slots=5,
        extra_jokers=[JokerStencil(), EggJoker()],
    )

    # One ordinary Joker consumes a slot, so both Stencils provide X4.
    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 256
