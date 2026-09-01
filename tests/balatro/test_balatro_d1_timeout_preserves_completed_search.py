from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import (
    LiveBlindPlan,
    LiveBlindPlanValue,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.hand_action_policy import (
    LiveHandActionDecisionEngine,
    PACE_PLAY,
)


def _plan(score: float = 200.0) -> LiveBlindPlan:
    return LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=[]),
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.5,
            expected_score=score,
            expected_hands_remaining=2.0,
            expected_discards_remaining=2.0,
        ),
        horizon=2,
        exact=False,
        candidate_count=1,
    )


def test_deeper_timeout_preserves_last_completed_search_instead_of_structural_fallback(monkeypatch):
    """A timed-out deeper probe must not erase already-computed Joker-aware D1 plans."""
    engine = LiveHandActionDecisionEngine(max_search_seconds=8.0)
    state = SimpleNamespace(
        hands_remaining=4,
        discards_remaining=3,
        score=0,
        blind=SimpleNamespace(requirement=400),
        hand=[],
    )
    completed = [_plan()]
    calls = 0

    def fake_rank_plans(current_state, *, planner=None):
        nonlocal calls
        del current_state, planner
        calls += 1
        if calls == 1:
            return completed
        raise PlannerSearchBudgetExceeded("deeper probe exhausted wall-clock budget")

    monkeypatch.setattr(engine, "rank_plans", fake_rank_plans)
    monkeypatch.setattr(engine, "_budget_exhausted", lambda: calls >= 2)
    monkeypatch.setattr(
        engine,
        "_structural_timeout_fallback",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("completed search must be used before structural timeout fallback")
        ),
    )
    monkeypatch.setattr(
        engine.policy.evaluator,
        "project_play",
        lambda state, action: SimpleNamespace(expected_hand_score=200.0),
    )
    monkeypatch.setattr(engine.policy.evaluator, "evaluate", lambda state, action: 0.0)

    decision = engine.decide(state)

    assert calls == 2
    assert decision.mode == PACE_PLAY
    assert decision.selected_plan is completed[0]
    assert decision.search_attempts[0].best_action == PLAY_CARDS
    assert decision.search_attempts[1].budget_exceeded
