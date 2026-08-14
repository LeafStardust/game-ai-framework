from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
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
    def __init__(self, config, *, confirmation=False):
        self.config = config
        self.confirmation = confirmation
        self.nodes_evaluated = 10


class _TestEngine(LiveHandActionDecisionEngine):
    def __init__(
        self,
        *,
        adaptive_by_horizon,
        fallback_plans,
        policy,
        confirmation_by_horizon=None,
        max_horizon=3,
    ):
        self._adaptive_by_horizon = dict(adaptive_by_horizon)
        self._confirmation_by_horizon = dict(confirmation_by_horizon or {})
        self._fallback_plans = list(fallback_plans)
        super().__init__(
            planner=_StubRootPlanner(policy.evaluator),
            policy=policy,
            max_horizon=max_horizon,
            max_search_nodes=5000,
        )

    def _adaptive_planner(self, config):
        return _AdaptiveStub(config, confirmation=False)

    def _confirmation_config(self, config):
        return config

    def _confirmation_planner(self, config):
        return _AdaptiveStub(config, confirmation=True)

    def rank_plans(self, state, *, planner=None):
        if planner is None or planner is self.planner:
            return list(self._fallback_plans)
        if getattr(planner, "confirmation", False):
            return list(self._confirmation_by_horizon[planner.config.horizon])
        return list(self._adaptive_by_horizon[planner.config.horizon])

    def _rank_immediate_plans(self, state):
        return list(self._fallback_plans)


# Production builds confirmation planners through _adaptive_planner. This test
# harness marks confirmation by temporarily routing the engine helper explicitly.
class _ConfirmationTestEngine(_TestEngine):
    def decide(self, state):
        original = self._adaptive_planner

        def routed(config):
            if getattr(self, "_next_is_confirmation", False):
                self._next_is_confirmation = False
                return self._confirmation_planner(config)
            return original(config)

        original_confirmation_config = self._confirmation_config

        def marked_confirmation_config(config):
            self._next_is_confirmation = True
            return original_confirmation_config(config)

        self._adaptive_planner = routed
        self._confirmation_config = marked_confirmation_config
        try:
            return super().decide(state)
        finally:
            self._adaptive_planner = original
            self._confirmation_config = original_confirmation_config
            self._next_is_confirmation = False


def _state(*cards):
    return SimpleNamespace(
        phase="SELECTING_HAND",
        hand=list(cards),
        score=0,
        blind=SimpleNamespace(requirement=300),
        hands_remaining=2,
        discards_remaining=0,
    )


def _plan(action_name, *, clear, immediate_score, marker, exact=False):
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
        exact=exact,
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


def test_adaptive_engine_stops_immediately_for_exact_clear_path():
    clear_marker = object()
    fallback_marker = object()
    accepted = _plan(
        PLAY_CARDS,
        clear=0.80,
        immediate_score=50.0,
        marker=clear_marker,
        exact=True,
    )
    fallback = _plan(
        PLAY_CARDS,
        clear=0.0,
        immediate_score=200.0,
        marker=fallback_marker,
    )
    engine = _TestEngine(
        adaptive_by_horizon={2: [accepted]},
        fallback_plans=[fallback],
        policy=_policy(),
    )

    decision = engine.decide(_state(clear_marker, fallback_marker))

    assert decision.mode == CLEAR_PATH
    assert decision.action.cards == [clear_marker]
    assert decision.sampled_clear_path_confirmed is False
    assert len(decision.search_attempts) == 1
    assert decision.search_attempts[0].horizon == 2
    assert decision.search_attempts[0].confirmation is False


def test_sampled_clear_path_requires_stronger_same_action_confirmation():
    clear_marker = object()
    fallback_marker = object()
    sampled = _plan(
        PLAY_CARDS,
        clear=1.0,
        immediate_score=50.0,
        marker=clear_marker,
        exact=False,
    )
    confirmed = _plan(
        PLAY_CARDS,
        clear=0.84,
        immediate_score=50.0,
        marker=clear_marker,
        exact=False,
    )
    fallback = _plan(
        PLAY_CARDS,
        clear=0.0,
        immediate_score=200.0,
        marker=fallback_marker,
    )
    engine = _ConfirmationTestEngine(
        adaptive_by_horizon={2: [sampled]},
        confirmation_by_horizon={2: [confirmed]},
        fallback_plans=[fallback],
        policy=_policy(),
        max_horizon=2,
    )

    decision = engine.decide(_state(clear_marker, fallback_marker))

    assert decision.mode == CLEAR_PATH
    assert decision.action.cards == [clear_marker]
    assert decision.sampled_clear_path_confirmed is True
    assert decision.confidence == 0.84
    assert len(decision.search_attempts) == 2
    assert decision.search_attempts[1].confirmation is True


def test_sampled_clear_path_is_rejected_when_confirmation_changes_first_action():
    first_marker = object()
    changed_marker = object()
    pace_marker = object()
    sampled = _plan(
        PLAY_CARDS,
        clear=0.90,
        immediate_score=50.0,
        marker=first_marker,
        exact=False,
    )
    changed = _plan(
        PLAY_CARDS,
        clear=0.90,
        immediate_score=50.0,
        marker=changed_marker,
        exact=False,
    )
    pace_play = _plan(
        PLAY_CARDS,
        clear=0.20,
        immediate_score=160.0,
        marker=pace_marker,
    )
    engine = _ConfirmationTestEngine(
        adaptive_by_horizon={2: [sampled]},
        confirmation_by_horizon={2: [changed]},
        fallback_plans=[pace_play],
        policy=_policy(),
        max_horizon=2,
    )

    decision = engine.decide(_state(first_marker, changed_marker, pace_marker))

    assert decision.mode == PACE_PLAY
    assert decision.action.cards == [pace_marker]
    assert decision.sampled_clear_path_confirmed is False
    assert len(decision.search_attempts) == 2
    assert decision.search_attempts[1].confirmation is True


def test_adaptive_engine_enters_pace_fallback_when_no_clear_path_exists():
    search_marker = object()
    pace_marker = object()
    below_floor = _plan(
        PLAY_CARDS,
        clear=0.40,
        immediate_score=80.0,
        marker=search_marker,
    )
    pace_play = _plan(
        PLAY_CARDS,
        clear=0.20,
        immediate_score=160.0,
        marker=pace_marker,
    )
    engine = _TestEngine(
        adaptive_by_horizon={
            2: [below_floor],
        },
        fallback_plans=[pace_play],
        policy=_policy(),
        max_horizon=2,
    )

    decision = engine.decide(_state(search_marker, pace_marker))

    assert decision.mode == PACE_PLAY
    assert decision.action.cards == [pace_marker]
    assert decision.pace_target == 150.0
    assert len(decision.search_attempts) == 1
