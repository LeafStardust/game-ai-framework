from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.card import BalatroCard
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.joker_policy import HOLD
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.state import BalatroState


class _FlatProjection:
    clear_probability = 0.0
    hand_score = 100
    expected_hand_score = 100.0
    maximum_hand_score = 100


class _TieEvaluator:
    def project_play(self, state, action):
        del state, action
        return _FlatProjection()


def _red_white_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.money = 30
    state.ante = 3
    state.joker_slots = 5
    return state


def test_scary_face_direction_vetoes_ride_the_bus_conflict():
    state = _red_white_state()
    state.jokers = [ScaryFaceJoker()]
    policy = PlaybookJokerAcquisitionPolicy(JokerBuildTransitionPlanner())

    decision = policy.decide(state, RideTheBusJoker())

    assert decision.action == HOLD
    assert any("canonical Bond conflict veto" in note for note in decision.rationale)
    assert any(
        "face_cards" in note and "no_face_cards" in note
        for note in decision.rationale
    )


def test_hanging_chad_never_leaves_debuffed_selected_card_first_on_projection_tie():
    debuffed = BalatroCard("K", "Hearts", debuffed=True)
    live = BalatroCard("K", "Spades", debuffed=False)
    filler = BalatroCard("5", "Clubs")
    state = SimpleNamespace(
        phase="SELECTING_HAND",
        jokers=[HangingChadJoker()],
        hand=[debuffed, live, filler],
    )
    action = BalatroAction(PLAY_CARDS, cards=[debuffed, live])

    decision = HandOrderPolicy().recommend(state, action, evaluator=_TieEvaluator())

    assert decision is not None
    # Original positions 0 and 1 must be swapped so the live King is first.
    assert decision.permutation[:2] == (1, 0)
    assert any("live first card" in note for note in decision.rationale)
