from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


def _value(probability: float = 0.8) -> LiveBlindPlanValue:
    return LiveBlindPlanValue(
        clear_probability=probability,
        expected_progress=probability,
        expected_score=100.0,
        expected_hands_remaining=1.0,
        expected_discards_remaining=1.0,
    )


class _ConfirmationPlanner:
    def __init__(self, expected_action):
        self.horizon = 5
        self.nodes_evaluated = 0
        self.expected_action = expected_action
        self.estimated = []

    def _require_state(self, state):
        assert state.phase == "SELECTING_HAND"

    def reset_search_stats(self):
        self.nodes_evaluated = 0

    def _candidate_actions(self, state, *, allow_discards):
        raise AssertionError("confirmation must not enumerate root candidates")

    def _estimate_action(self, state, action, depth):
        assert action is self.expected_action
        assert depth == self.horizon
        self.nodes_evaluated += 1
        self.estimated.append(action)
        return SimpleNamespace(action=action, value=_value(), exact=False)

    @staticmethod
    def _estimate_key(estimate):
        return (estimate.value.clear_probability,)


def test_confirmation_reestimates_only_original_first_action():
    marker = object()
    state = SimpleNamespace(phase="SELECTING_HAND", hand=[marker])
    action = BalatroAction(PLAY_CARDS, cards=[marker])
    original = LiveBlindPlan(
        action=action,
        value=_value(0.75),
        horizon=5,
        exact=False,
        candidate_count=4,
    )
    planner = _ConfirmationPlanner(action)
    engine = LiveHandActionDecisionEngine.__new__(LiveHandActionDecisionEngine)

    confirmed = engine._confirm_plan(state, original, planner=planner)

    assert confirmed.action is action
    assert confirmed.candidate_count == 1
    assert planner.estimated == [action]
    assert planner.nodes_evaluated == 1
    assert not hasattr(planner, "_confirmation_root_action")
