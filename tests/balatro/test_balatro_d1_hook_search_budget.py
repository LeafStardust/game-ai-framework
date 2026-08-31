from types import SimpleNamespace

import games.balatro.d1_hook_search_budget_policy as policy


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
