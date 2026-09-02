from types import SimpleNamespace

import pytest

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.state import BalatroState


def _state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("K", "Hearts", live_id=2),
        BalatroCard("7", "Clubs", live_id=3),
        BalatroCard("3", "Diamonds", live_id=4),
    ]
    state.deck = [BalatroCard("2", "Clubs", live_id=5)]
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 1000)
    state.jokers = []
    return state


def test_root_candidate_admission_does_not_project_plays_or_score_discards(monkeypatch):
    planner = D1LiveBlindClearPlanner(play_width=4, discard_width=2, horizon=2)
    state = _state()

    def forbidden(*args, **kwargs):
        raise AssertionError("root admission entered expensive D1 evaluation")

    monkeypatch.setattr(planner, "_play_projection", forbidden)
    monkeypatch.setattr(planner, "_discard_priority", forbidden)

    candidates = planner._candidate_actions(state, allow_discards=True)

    assert candidates
    assert planner.nodes_evaluated == 0
    assert any(action.name == PLAY_CARDS for action in candidates)
    assert any(action.name == DISCARD_CARDS for action in candidates)


def test_play_projection_rechecks_deadline_after_expensive_evaluator(monkeypatch):
    planner = D1LiveBlindClearPlanner(play_width=1, discard_width=0, horizon=1)
    state = _state()
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
    planner.deadline = 1.0

    ticks = iter((0.0, 2.0))
    monkeypatch.setattr(
        "games.balatro.live.hand_action_planner_core.perf_counter",
        lambda: next(ticks),
    )
    monkeypatch.setattr(
        planner.evaluator,
        "project_play",
        lambda *args, **kwargs: SimpleNamespace(clears_blind=False),
    )

    with pytest.raises(PlannerSearchBudgetExceeded, match="wall-clock budget"):
        planner._play_projection(state, action)

    assert planner.play_projections_evaluated == 0
