from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.adaptive_search import AdaptiveBlindSearchConfig
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_policy import (
    PACE_RECOVERY,
    LiveHandActionDecisionEngine,
)


class _Planner:
    def __init__(self, state):
        self.evaluator = object()
        self.action_generator = object()
        self.play_width = 6
        self.discard_width = 4
        self.horizon = 2
        self.max_nodes = 500
        self.deadline = None
        self.nodes_evaluated = 0
        self._state = state

    def _require_state(self, state):
        assert state is self._state

    def _child_play_candidates(self, state, play_limit):
        del play_limit
        return [BalatroAction(PLAY_CARDS, cards=[state.hand[0]])]


class _Policy:
    def __init__(self):
        self.thresholds = SimpleNamespace(setup_discard_consensus_agreement=3)

    @staticmethod
    def _pace_target(state):
        return float(state.blind.requirement - state.score) / state.hands_remaining

    def _decision(self, **kwargs):
        return SimpleNamespace(
            mode=kwargs["mode"],
            action=kwargs["selected"].action,
            selected_plan=kwargs["selected"],
            search_attempts=kwargs["search_attempts"],
            rationale=kwargs["rationale"],
        )


def _config():
    return AdaptiveBlindSearchConfig(
        horizon=2,
        samples=8,
        child_samples=2,
        play_width=6,
        discard_width=4,
        child_play_width=4,
        child_discard_width=2,
        max_nodes=500,
    )


def test_expired_d1_budget_skips_unbounded_immediate_recovery(monkeypatch):
    state = SimpleNamespace(
        phase="SELECTING_HAND",
        hand=[object(), object(), object()],
        hands_remaining=4,
        discards_remaining=5,
        score=0,
        blind=SimpleNamespace(requirement=100000),
    )
    planner = _Planner(state)
    policy = _Policy()
    engine = LiveHandActionDecisionEngine(
        planner=planner,
        policy=policy,
        max_horizon=2,
        max_search_nodes=500,
        max_search_seconds=1e-9,
    )

    adaptive = SimpleNamespace(nodes_evaluated=0)
    monkeypatch.setattr(engine, "_search_schedule", lambda current: (_config(),))
    monkeypatch.setattr(engine, "_adaptive_planner", lambda config: adaptive)

    def budget_exceeded(current, *, planner=None):
        raise PlannerSearchBudgetExceeded("forced wall-clock expiry")

    monkeypatch.setattr(engine, "rank_plans", budget_exceeded)
    monkeypatch.setattr(
        engine,
        "_rank_immediate_plans",
        lambda current: (_ for _ in ()).throw(
            AssertionError("expired D1 budget must not enter immediate recovery")
        ),
    )

    decision = engine.decide(state)

    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == PLAY_CARDS
    assert decision.action.cards == [state.hand[0]]
    assert "wall-clock budget exhausted" in decision.rationale[0]
