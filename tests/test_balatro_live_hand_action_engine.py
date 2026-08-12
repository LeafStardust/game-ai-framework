from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)


class _FakeEvaluator:
    def project_play(self, state, action):
        return SimpleNamespace(expected_hand_score=float(action.target["immediate_score"]))

    def evaluate(self, state, action):
        return float(action.target.get("fallback_value", 0.0))


class _StubRootPlanner:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.action_generator = object()


class _AdaptiveStub:
    def __init__(self, config):
        self.config = config
        self.nodes_evaluated = 10


class _TestEngine(LiveHandActionDecisionEngine):
    def __init__(self, *, adaptive_by_horizon, fallback_plans, policy):
        self._adaptive_by_horizon = dict(adaptive_by_horizon)
        self._fallback_plans = list(fallback_plans)
        super().__init__(
            planner=_StubRootPlanner(policy.evaluator),
            policy=policy,
            max_horizon=3,
            max_search_nodes=5000,
        )

    def _adaptive_planner(self, config):
        return _AdaptiveStub(config)

    def rank_plans(self, state, *, planner=None):
        if planner is None or planner is self.planner:
            return list(self._fallback_plans)
        return list(self._adaptive_by_horizon[planner.config.horizon])


def _state():
    return SimpleNamespace(
        phase="SELECTING_HAND",
        score=0,
        blind=SimpleNamespace(requirement=300),
        hands_remaining=2,
        discards_remaining=0,
    )


def _plan(action_name, *, clear, immediate_score, marker):
    action = BalatroAction(
        action_name,
        cards=[marker],
        target={"immediate_score": immediate_score, "fallback_value": immediate_score},
    )
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear,
            expected_progress=min(1.0, immediate_score / 300.0),
            expected_score=immediate_score,
            expected_hands_remaining=1.0,
            expected_discards_remaining=0.0,
        ),
        horizon=2,
        exact=False,
        candidate_count=1,
    )


def _policy():
    return LiveHandActionPolicy(
        HandActionThresholds(
            clear_path_probability_floor=0.75,
            pace_ratio_floor=1.0,
        ),
        evaluator=_FakeEvaluator(),
    )


def test_adaptive_engine_stops_when_a_clear_path_reaches_floor():
    accepted = _plan(
        PLAY_CARDS,
        clear=0.80,
        immediate_score=50.0,
        marker="clear-path",
    )
    fallback = _plan(
        PLAY_CARDS,
        clear=0.0,
        immediate_score=200.0,
        marker="fallback",
    )
    engine = _TestEngine(
        adaptive_by_horizon={2: [accepted]},
        fallback_plans=[fallback],
        policy=_policy(),
    )

    decision = engine.decide(_state())

    assert decision.mode == CLEAR_PATH
    assert decision.action.cards == ["clear-path"]
    assert len(decision.search_attempts) == 1
    assert decision.search_attempts[0].horizon == 2


def test_adaptive_engine_enters_pace_fallback_when_no_clear_path_exists():
    below_floor = _plan(
        PLAY_CARDS,
        clear=0.40,
        immediate_score=80.0,
        marker="search",
    )
    pace_play = _plan(
        PLAY_CARDS,
        clear=0.20,
        immediate_score=160.0,
        marker="pace",
    )
    engine = _TestEngine(
        adaptive_by_horizon={
            2: [below_floor],
        },
        fallback_plans=[pace_play],
        policy=_policy(),
    )

    decision = engine.decide(_state())

    assert decision.mode == PACE_PLAY
    assert decision.action.cards == ["pace"]
    assert decision.pace_target == 150.0
    assert len(decision.search_attempts) == 1
