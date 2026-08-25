from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _cerulean_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = "Cerulean Bell"
    state.blind = Blind(BlindType.BOSS, 100_000)
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.hand_size = 5
    state.hand = [
        BalatroCard("A", "Spades", live_id=1, forced_selection=True),
        BalatroCard("K", "Hearts", live_id=2),
        BalatroCard("9", "Clubs", live_id=3),
        BalatroCard("6", "Diamonds", live_id=4),
        BalatroCard("2", "Spades", live_id=5),
    ]
    return state


def test_cerulean_forced_card_is_present_in_every_d1_play_and_discard_candidate():
    state = _cerulean_state()
    forced = state.hand[0]
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=5,
        child_play_width=4,
        child_discard_width=5,
        horizon=2,
    )

    actions = planner._candidate_actions(state, allow_discards=True)
    controlled = [
        action
        for action in actions
        if action.name in {PLAY_CARDS, DISCARD_CARDS}
    ]

    assert any(action.name == PLAY_CARDS for action in controlled)
    assert any(action.name == DISCARD_CARDS for action in controlled)
    assert all(forced in action.cards for action in controlled)


def test_cerulean_child_discard_candidates_are_filtered_by_same_forced_card_rule():
    state = _cerulean_state()
    forced = state.hand[0]
    planner = D1LiveBlindClearPlanner(
        play_width=4,
        discard_width=5,
        child_play_width=4,
        child_discard_width=5,
        horizon=2,
    )

    # One consumed node makes the planner build its bounded recursive child beam
    # instead of the exhaustive root beam.
    planner.nodes_evaluated = 1
    actions = planner._candidate_actions(state, allow_discards=True)
    discards = [action for action in actions if action.name == DISCARD_CARDS]

    assert discards
    assert all(forced in action.cards for action in discards)
