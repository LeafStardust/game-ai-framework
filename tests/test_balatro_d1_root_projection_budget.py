from __future__ import annotations

from itertools import combinations
from types import SimpleNamespace
from time import perf_counter

import pytest

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
import games.balatro.live.hand_action_planner_core as planner_module


class _FakeEvaluator:
    def __init__(self):
        self.project_calls = 0

    def project_play(self, state, action):
        self.project_calls += 1
        return SimpleNamespace(
            clears_blind=False,
            clear_probability=0.0,
            expected_hand_score=float(len(action.cards)),
            hand_score=len(action.cards),
        )


class _ExhaustiveGenerator:
    MAX_SELECTED_CARDS = 5

    def generate_play_actions(self, state):
        actions = []
        for amount in range(1, min(5, len(state.hand)) + 1):
            for cards in combinations(state.hand, amount):
                actions.append(BalatroAction(PLAY_CARDS, cards=list(cards)))
        return actions


def _planner(monkeypatch):
    evaluator = _FakeEvaluator()
    planner = D1LiveBlindClearPlanner(
        evaluator=evaluator,
        action_generator=_ExhaustiveGenerator(),
        horizon=2,
        max_nodes=500,
    )
    monkeypatch.setattr(
        planner_module,
        "boss_play_action_is_legal",
        lambda state, action: True,
    )
    monkeypatch.setattr(
        planner,
        "_direct_child_play_priority",
        lambda action: (len(action.cards), tuple(id(card) for card in action.cards)),
    )
    monkeypatch.setattr(planner, "_child_play_candidates", lambda state, limit: [])
    return planner, evaluator


def test_root_prebeam_caps_expensive_projection_candidates(monkeypatch):
    planner, evaluator = _planner(monkeypatch)
    state = SimpleNamespace(hand=[object() for _ in range(8)], blind=None)

    candidates = planner._root_play_candidates(state, play_limit=6)
    for action in candidates:
        planner._play_projection(state, action)

    assert len(candidates) <= planner._MAX_ROOT_PROJECTED_PLAYS == 24
    assert evaluator.project_calls <= 24


def test_root_projection_checks_wall_clock_before_expensive_evaluator(monkeypatch):
    planner, evaluator = _planner(monkeypatch)
    state = SimpleNamespace(hand=[object() for _ in range(8)], blind=None)
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
    planner.deadline = perf_counter() - 0.001

    with pytest.raises(PlannerSearchBudgetExceeded, match="wall-clock budget"):
        planner._play_projection(state, action)

    assert evaluator.project_calls == 0
