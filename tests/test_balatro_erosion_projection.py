from games.balatro.card import BalatroCard
from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.hand import PokerHand
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(*, deck_name="RED", owned_count=52, owned_known=True):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.deck_name = deck_name
    state.hand = [ace]
    # Remaining drawable composition must not affect Erosion.
    state.deck = []
    if owned_known:
        state.owned_deck = [
            BalatroCard("2", "Clubs")
            for _ in range(owned_count)
        ]
    state.jokers = [ErosionJoker()]

    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )


def test_standard_starting_deck_sizes_keep_abandoned_distinct():
    assert starting_deck_size_for_name("RED") == 52
    assert starting_deck_size_for_name("ERRATIC") == 52
    assert starting_deck_size_for_name("ABANDONED") == 40
    assert starting_deck_size_for_name("CUSTOM") is None


def test_erosion_uses_full_owned_deck_below_standard_52_card_baseline():
    transition = _project(deck_name="RED", owned_count=50)

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 144


def test_erosion_uses_abandoned_40_card_starting_baseline():
    transition = _project(deck_name="ABANDONED", owned_count=38)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 144


def test_erosion_never_penalizes_decks_above_starting_size():
    transition = _project(deck_name="RED", owned_count=60)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 16


def test_erosion_fails_closed_without_authoritative_owned_deck():
    transition = _project(owned_known=False)

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Erosion",)
    assert transition.distribution.minimum == 16


def test_erosion_fails_closed_for_unknown_starting_deck_baseline():
    transition = _project(deck_name="CUSTOM", owned_count=40)

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Erosion",)
    assert transition.distribution.minimum == 16
