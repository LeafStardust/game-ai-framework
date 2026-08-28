from types import SimpleNamespace

import games.balatro.d1_hook_search_budget_policy as policy


def test_active_hook_temporarily_caps_configured_d1_search_budget(monkeypatch):
    engine = SimpleNamespace(max_search_seconds=8.0)
    state = SimpleNamespace(boss_name="The Hook")
    observed = []

    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    def original(self, state):
        del state
        observed.append(self.max_search_seconds)
        return "decision"

    result = policy._decide_with_hook_search_cap(original, engine, state)

    assert result == "decision"
    assert observed == [policy._HOOK_MAX_SEARCH_SECONDS]
    assert engine.max_search_seconds == 8.0


def test_hook_search_budget_restores_after_exception(monkeypatch):
    engine = SimpleNamespace(max_search_seconds=8.0)
    state = SimpleNamespace(boss_name="The Hook")

    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    def original(self, state):
        del state
        assert self.max_search_seconds == policy._HOOK_MAX_SEARCH_SECONDS
        raise RuntimeError("boom")

    try:
        policy._decide_with_hook_search_cap(original, engine, state)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected original decision failure")

    assert engine.max_search_seconds == 8.0


def test_non_hook_keeps_configured_d1_search_budget(monkeypatch):
    engine = SimpleNamespace(max_search_seconds=8.0)
    state = SimpleNamespace(boss_name="The Window")
    observed = []

    monkeypatch.setattr(policy, "_active_hook", lambda state: False)

    def original(self, state):
        del state
        observed.append(self.max_search_seconds)
        return "decision"

    assert policy._decide_with_hook_search_cap(original, engine, state) == "decision"
    assert observed == [8.0]
    assert engine.max_search_seconds == 8.0


def test_existing_tighter_hook_budget_is_not_relaxed(monkeypatch):
    engine = SimpleNamespace(max_search_seconds=2.0)
    state = SimpleNamespace(boss_name="The Hook")
    observed = []

    monkeypatch.setattr(policy, "_active_hook", lambda state: True)

    def original(self, state):
        del state
        observed.append(self.max_search_seconds)
        return "decision"

    assert policy._decide_with_hook_search_cap(original, engine, state) == "decision"
    assert observed == [2.0]
    assert engine.max_search_seconds == 2.0
