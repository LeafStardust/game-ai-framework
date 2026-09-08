from types import SimpleNamespace

import pytest

from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def test_native_bond_intent_cache_reuses_current_decision_state(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    state = SimpleNamespace()
    cached = (("PAIR", 2.0, "pair_engine"),)

    policy._bond_d1_cached_state_id = id(state)
    policy._bond_d1_cached_intents = cached

    def composition_must_not_run(current_state):
        del current_state
        raise AssertionError("cached Bond intents should not recompute composition")

    monkeypatch.setattr(policy, "_composition", composition_must_not_run)

    assert policy._hand_bond_intents(state) == list(cached)


def test_native_bond_intent_cache_clears_after_failed_decision(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    state = SimpleNamespace()
    calls = []

    def empty_composition(current_state):
        calls.append(current_state)
        return (), None

    monkeypatch.setattr(policy, "_composition", empty_composition)

    with pytest.raises(ValueError, match="D1 requires at least one PLAY_CARDS candidate"):
        policy.decide(state, ())

    assert calls == [state]
    assert policy._bond_d1_cached_state_id is None
    assert policy._bond_d1_cached_intents is None
