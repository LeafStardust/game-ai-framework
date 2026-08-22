from types import SimpleNamespace

import games.balatro.live.path_aware_hand_action_engine as module
from games.balatro.live.path_aware_hand_action_engine import PathAwareLiveHandActionDecisionEngine


def test_path_aware_engine_evaluates_health_after_final_selected_plan(monkeypatch):
    selected_plan = object()
    decision = SimpleNamespace(
        mode="PACE_PLAY",
        setup_discard_consensus=False,
        selected_plan=selected_plan,
    )
    sentinel_health = object()
    seen = {}

    def fake_base_decide(self, state):
        return decision

    def fake_health(state, *, selected_plan):
        seen["state"] = state
        seen["selected_plan"] = selected_plan
        return sentinel_health

    monkeypatch.setattr(module._BaseLiveHandActionDecisionEngine, "decide", fake_base_decide)
    monkeypatch.setattr(module, "evaluate_live_strategy_health", fake_health)

    engine = PathAwareLiveHandActionDecisionEngine.__new__(PathAwareLiveHandActionDecisionEngine)
    engine._adaptive_root_history = []
    engine._record_adaptive_roots = False
    engine.last_strategy_health = None
    monkeypatch.setattr(engine, "_apply_consensus_recovery", lambda state, value: value)

    state = object()
    result = engine.decide(state)

    assert result is decision
    assert seen == {"state": state, "selected_plan": selected_plan}
    assert engine.last_strategy_health is sentinel_health
