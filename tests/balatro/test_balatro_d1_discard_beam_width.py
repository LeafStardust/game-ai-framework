from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("A", "Spades", live_id=0),
        BalatroCard("K", "Hearts", live_id=1),
        BalatroCard("Q", "Clubs", live_id=2),
        BalatroCard("9", "Diamonds", live_id=3),
        BalatroCard("4", "Spades", live_id=4),
    ]
    state.discards_remaining = 3
    return state


def test_width_one_discard_beam_selects_best_discard_overall_not_one_card_only():
    state = _state()
    planner = D1LiveBlindClearPlanner()
    discards = [
        BalatroAction(DISCARD_CARDS, cards=state.hand[:amount])
        for amount in range(1, 6)
    ]
    planner._discard_priority = lambda current_state, action: float(len(action.cards))

    selected = planner._diverse_discard_beam(state, discards, 1)

    assert len(selected) == 1
    assert len(selected[0].cards) == 5


def test_wider_discard_beam_preserves_distinct_redraw_sizes_from_priority_order():
    state = _state()
    planner = D1LiveBlindClearPlanner()
    discards = [
        BalatroAction(DISCARD_CARDS, cards=state.hand[:amount])
        for amount in range(1, 6)
    ]
    planner._discard_priority = lambda current_state, action: float(len(action.cards))

    selected = planner._diverse_discard_beam(state, discards, 3)

    assert [len(action.cards) for action in selected] == [5, 4, 3]
