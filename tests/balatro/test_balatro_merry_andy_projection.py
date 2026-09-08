from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def test_merry_andy_declares_correct_passive_modifiers():
    context = JokerContext(
        state=BalatroState(),
        trigger="JOKER_ACQUIRED",
        data={},
    )

    result = MerryAndyJoker().apply(context)

    assert result.data["hand_size_modifier"] == -1
    assert result.data["discards_per_round_modifier"] == 3


def test_merry_andy_is_score_neutral_during_live_blind_projection():
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = []
    state.jokers = [MerryAndyJoker()]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.maximum == 16
