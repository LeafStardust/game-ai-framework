from types import SimpleNamespace

import games.balatro.d1_hook_search_budget_policy as policy
import games.balatro.live.path_aware_hand_action_engine as path_engine
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


def test_active_hook_caps_configured_d1_search_budget(monkeypatch):
    state = SimpleNamespace(boss_name="The Hook")
    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    assert policy.effective_d1_search_seconds(state, 8.0) == policy._HOOK_MAX_SEARCH_SECONDS


def test_non_hook_keeps_configured_d1_search_budget(monkeypatch):
    state = SimpleNamespace(boss_name="The Window")
    monkeypatch.setattr(policy, "_active_hook", lambda state: False)

    assert policy.effective_d1_search_seconds(state, 8.0) == 8.0


def test_existing_tighter_hook_budget_is_not_relaxed(monkeypatch):
    state = SimpleNamespace(boss_name="The Hook")
    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    assert policy.effective_d1_search_seconds(state, 2.0) == 2.0


def test_unbounded_d1_search_stays_unbounded_for_hook(monkeypatch):
    state = SimpleNamespace(boss_name="The Hook")
    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    assert policy.effective_d1_search_seconds(state, None) is None


def test_path_aware_engine_applies_and_restores_hook_budget(monkeypatch):
    engine = path_engine.PathAwareLiveHandActionDecisionEngine(max_search_seconds=8.0)
    state = SimpleNamespace(boss_name="The Hook")
    decision = SimpleNamespace(selected_plan=object())
    observed = []

    monkeypatch.setattr(
        path_engine,
        "effective_d1_search_seconds",
        lambda state, configured: policy._HOOK_MAX_SEARCH_SECONDS,
    )

    def base_decide(self, state):
        del state
        observed.append(self.max_search_seconds)
        return decision

    monkeypatch.setattr(LiveHandActionDecisionEngine, "decide", base_decide)
    monkeypatch.setattr(
        path_engine.PathAwareLiveHandActionDecisionEngine,
        "_apply_adaptive_authority",
        lambda self, state, value: value,
    )
    monkeypatch.setattr(
        path_engine.PathAwareLiveHandActionDecisionEngine,
        "_apply_consensus_recovery",
        lambda self, state, value: value,
    )
    monkeypatch.setattr(path_engine, "evaluate_live_strategy_health", lambda *args, **kwargs: None)

    assert engine.decide(state) is decision
    assert observed == [policy._HOOK_MAX_SEARCH_SECONDS]
    assert engine.max_search_seconds == 8.0
