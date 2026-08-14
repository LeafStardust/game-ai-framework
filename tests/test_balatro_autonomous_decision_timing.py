from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.live.external import live_memory_autonomous_step_injected as target


def test_hand_recommendation_reports_total_and_per_search_timing(monkeypatch):
    card = object()
    state = SimpleNamespace(hand=[card])
    action = BalatroAction(DISCARD_CARDS, cards=[card])
    selected_plan = SimpleNamespace(
        action=action,
        value=SimpleNamespace(clear_probability=0.0),
        exact=True,
    )
    attempts = (
        SimpleNamespace(
            confirmation=False,
            horizon=2,
            samples=8,
            nodes_evaluated=100,
            max_nodes=2000,
            budget_exceeded=False,
            best_action=DISCARD_CARDS,
            best_clear_probability=0.125,
            best_expected_score=5000.0,
            best_exact=True,
        ),
        SimpleNamespace(
            confirmation=True,
            horizon=2,
            samples=32,
            nodes_evaluated=150,
            max_nodes=2000,
            budget_exceeded=True,
            best_action=None,
            best_clear_probability=None,
            best_expected_score=None,
            best_exact=None,
        ),
    )
    decision = SimpleNamespace(
        mode="PACE_RECOVERY",
        confidence=0.48,
        action=action,
        selected_plan=selected_plan,
        selected_pace_ratio=None,
        search_attempts=attempts,
    )

    class FakeEngine:
        def __init__(self, **kwargs):
            del kwargs

        def rank_plans(self, current_state, *, planner=None):
            del current_state, planner
            return []

        def decide(self, current_state):
            del current_state
            self.rank_plans(state, planner=object())
            self.rank_plans(state, planner=object())
            return decision

    playbook = SimpleNamespace(
        name="red-white",
        version="0.5",
        strategy={"planner": {}, "decision_thresholds": {"hand_action": {}}},
    )
    monkeypatch.setattr(
        target,
        "default_balatro_playbooks",
        lambda: SimpleNamespace(for_state=lambda current: playbook),
    )
    monkeypatch.setattr(target, "LiveHandActionDecisionEngine", FakeEngine)

    clock = iter((0.0, 1.0, 2.0, 3.0, 5.0, 8.0))
    monkeypatch.setattr(target, "perf_counter", lambda: next(clock))

    runner = target.LiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )
    recommended, notes = runner._recommend_hand(state, None)

    assert recommended is action
    assert "d1_decision_seconds=8.000" in notes
    assert any(
        "search[0]=adaptive h=2 samples=8 nodes=100/2000" in note
        and "elapsed=1.000s" in note
        and "best_action=DISCARD_CARDS" in note
        and "best_clear_probability=0.125000" in note
        and "best_expected_score=5000.000" in note
        and "best_exact=True" in note
        for note in notes
    )
    assert any(
        "search[1]=confirmation h=2 samples=32 nodes=150/2000" in note
        and "budget_exceeded=True" in note
        and "elapsed=2.000s" in note
        and "best_action=NONE" in note
        and "best_clear_probability=NONE" in note
        and "best_expected_score=NONE" in note
        and "best_exact=NONE" in note
        for note in notes
    )
