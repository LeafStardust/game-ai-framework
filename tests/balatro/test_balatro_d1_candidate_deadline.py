from __future__ import annotations

from types import SimpleNamespace

import pytest

import games.balatro  # install package-level D1 deadline authority
import games.balatro.d1_candidate_deadline_policy as deadline_policy
from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


class _Actions:
    def __init__(self, actions):
        self.actions = list(actions)

    def generate_play_actions(self, state):
        return list(self.actions)

    def generate_discard_actions(self, state):
        return []


class _Evaluator:
    def __init__(self):
        self.calls = 0

    def project_play(self, state, action):
        self.calls += 1
        score = float(len(action.cards))
        return SimpleNamespace(
            clear_probability=0.0,
            expected_hand_score=score,
            hand_score=score,
        )


def _actions():
    cards = [object(), object(), object()]
    return [
        BalatroAction(PLAY_CARDS, cards=[cards[0]]),
        BalatroAction(PLAY_CARDS, cards=[cards[0], cards[1]]),
        BalatroAction(PLAY_CARDS, cards=cards),
    ]


def test_expired_deadline_blocks_candidate_projection_before_first_node(monkeypatch):
    evaluator = _Evaluator()
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        action_generator=_Actions(_actions()),
        play_width=3,
        discard_width=0,
        horizon=2,
        deadline=5.0,
    )
    monkeypatch.setattr(deadline_policy, "perf_counter", lambda: 6.0)

    with pytest.raises(PlannerSearchBudgetExceeded, match="candidate generation"):
        planner._candidate_actions(
            SimpleNamespace(discards_remaining=0),
            allow_discards=False,
        )

    assert evaluator.calls == 0
    assert planner.nodes_evaluated == 0


def test_deadline_is_checked_between_expensive_candidate_projections(monkeypatch):
    evaluator = _Evaluator()
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        action_generator=_Actions(_actions()),
        play_width=3,
        discard_width=0,
        horizon=2,
        deadline=5.0,
    )
    # Candidate generation and the first projection begin before the deadline. The
    # post-projection check observes expiry, so the second expensive projection
    # must never start.
    clock = iter((0.0, 0.0, 1.0, 6.0))
    monkeypatch.setattr(deadline_policy, "perf_counter", lambda: next(clock))

    with pytest.raises(PlannerSearchBudgetExceeded, match="play candidate ranking"):
        planner._candidate_actions(
            SimpleNamespace(discards_remaining=0),
            allow_discards=False,
        )

    assert evaluator.calls == 1
    assert planner.nodes_evaluated == 0


def test_no_deadline_preserves_candidate_priority_order():
    evaluator = _Evaluator()
    actions = _actions()
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        action_generator=_Actions(actions),
        play_width=2,
        discard_width=0,
        horizon=2,
        deadline=None,
    )

    ranked = planner._candidate_actions(
        SimpleNamespace(discards_remaining=0),
        allow_discards=False,
    )

    assert [len(action.cards) for action in ranked] == [3, 2]
    assert evaluator.calls == 3
