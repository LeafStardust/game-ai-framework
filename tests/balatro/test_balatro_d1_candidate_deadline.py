from __future__ import annotations

from types import SimpleNamespace

import pytest

import games.balatro.live.blind_clear_planner as module
from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


class _Actions:
    def __init__(self, actions):
        self.actions = list(actions)

    def generate_play_actions(self, state):
        del state
        return list(self.actions)

    def generate_discard_actions(self, state):
        del state
        return []


class _Evaluator:
    def __init__(self):
        self.calls = 0

    def project_play(self, state, action):
        del state
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
    monkeypatch.setattr(module, "perf_counter", lambda: 6.0)

    with pytest.raises(PlannerSearchBudgetExceeded, match="wall-clock budget"):
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
    # Initial-root ranking is deliberately projection-free. Mark this as a later
    # candidate pass so the regression continues to cover deadline checks around
    # the Joker-aware priority projections retained for child/later search.
    planner.nodes_evaluated = 1

    checks = 0

    def check_deadline():
        nonlocal checks
        checks += 1
        if evaluator.calls >= 2:
            raise PlannerSearchBudgetExceeded(
                "live blind planner search exceeded wall-clock budget during candidate ranking"
            )

    monkeypatch.setattr(planner, "_check_deadline", check_deadline)
    monkeypatch.setattr(module, "perf_counter", lambda: 0.0)

    with pytest.raises(PlannerSearchBudgetExceeded, match="wall-clock budget"):
        planner._candidate_actions(
            SimpleNamespace(discards_remaining=0),
            allow_discards=False,
        )

    assert evaluator.calls == 2
    assert checks >= 3
    assert planner.nodes_evaluated == 1


def test_initial_root_bootstrap_stops_candidate_expansion(monkeypatch):
    evaluator = _Evaluator()
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        action_generator=_Actions(_actions()),
        play_width=3,
        discard_width=0,
        horizon=2,
        deadline=10.0,
    )
    planner.ROOT_CANDIDATE_BOOTSTRAP_SECONDS = 0.75

    now = 0.0

    def clock():
        nonlocal now
        value = now
        now += 0.2
        return value

    monkeypatch.setattr(module, "perf_counter", clock)

    ranked = planner._candidate_actions(
        SimpleNamespace(discards_remaining=0),
        allow_discards=False,
    )

    # Root bootstrap shaping must remain cheap: it may truncate the candidate beam
    # as time advances, but it must not invoke Joker-aware project_play at all.
    assert evaluator.calls == 0
    assert 1 <= len(ranked) <= len(_actions())
    assert planner.nodes_evaluated == 0


def test_no_deadline_preserves_candidate_priority_order(monkeypatch):
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
    # Child/later candidate passes still use the canonical Joker-aware priority.
    planner.nodes_evaluated = 1
    monkeypatch.setattr(module, "perf_counter", lambda: 0.0)

    ranked = planner._candidate_actions(
        SimpleNamespace(discards_remaining=0),
        allow_discards=False,
    )

    assert [len(action.cards) for action in ranked] == [3, 2]
    assert evaluator.calls == 3
