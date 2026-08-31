from time import perf_counter
from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import (
    LiveBlindPlanValue,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)


class _ImmediatePlanner:
    def __init__(self):
        self.evaluator = object()
        self.deadline = None
        self.nodes_evaluated = 0
        self.candidate_calls = 0
        self.estimate_calls = 0
        self.action = BalatroAction(PLAY_CARDS, cards=[object()])

    @staticmethod
    def _require_state(state):
        del state

    def reset_search_stats(self):
        self.nodes_evaluated = 0

    def _candidate_actions(self, state, *, allow_discards):
        del state
        assert allow_discards is True
        self.candidate_calls += 1
        return [self.action]

    def _estimate_action(self, state, action, depth):
        del state
        assert action is self.action
        assert depth == 1
        self.estimate_calls += 1
        return SimpleNamespace(
            action=action,
            value=LiveBlindPlanValue(
                clear_probability=0.0,
                expected_progress=0.0,
                expected_score=0.0,
                expected_hands_remaining=3.0,
                expected_discards_remaining=4.0,
            ),
            exact=True,
        )

    @staticmethod
    def _estimate_key(estimate):
        return (estimate.value.expected_score,)


def test_hard_budget_rejects_projected_immediate_pass_before_candidate_work():
    planner = _ImmediatePlanner()
    engine = PathAwareLiveHandActionDecisionEngine(
        planner=planner,
        max_search_seconds=2.1,
    )
    state = SimpleNamespace()

    engine._search_deadline = perf_counter() + 10.0
    with pytest.raises(PlannerSearchBudgetExceeded, match="immediate fallback under hard D1 budget"):
        engine._rank_immediate_plans(state)

    assert planner.candidate_calls == 0
    assert planner.estimate_calls == 0


def test_no_hard_deadline_preserves_projected_immediate_ranking():
    planner = _ImmediatePlanner()
    engine = PathAwareLiveHandActionDecisionEngine(
        planner=planner,
        max_search_seconds=None,
    )
    state = SimpleNamespace()

    plans = engine._rank_immediate_plans(state)

    assert len(plans) == 1
    assert planner.candidate_calls == 1
    assert planner.estimate_calls == 1
