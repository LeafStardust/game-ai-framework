from types import SimpleNamespace

import games.balatro.build_health_policy as policy
from games.balatro.build_health import BuildHealth


def _health():
    return BuildHealth(total=60.0, survival=80.0, immediate=80.0, scaling=60.0,
                       coherence=50.0, runway=50.0, critical=False, scaling_deficit=False,
                       warnings=(), engines=())


class _CountingHealth:
    def __init__(self): self.calls = 0
    def evaluate(self, state):
        del state
        self.calls += 1
        return _health()


def _state():
    joker = SimpleNamespace(name="Stateful", counter=1, mult=0, chips=0, x_mult=1.0,
                            eternal=False, edition=None)
    return SimpleNamespace(
        ante=4, round=2, phase="SHOP", money=30, score=0, blind_score=5000,
        hands_remaining=0, discards_remaining=0, hand_size=8, joker_slots=5,
        consumable_slots=2, last_played_hand=None, boss_name=None,
        boss_blind_state_observed=False, boss_blind_hands=set(), boss_blind_only_hand=None,
        jokers=[joker], consumables=[SimpleNamespace(name="The Hermit", used=False)],
        vouchers=[SimpleNamespace(name="Paint Brush")], hand_levels={"PAIR": 1},
        hand_play_counts={"PAIR": 0}, round_hand_play_counts={"PAIR": 0}, owned_deck=[], deck=[])


def test_cache_invalidates_when_opening_hand_size_changes(monkeypatch):
    health = _CountingHealth(); monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace(); state = _state()
    policy._cached_health(owner, state); policy._cached_health(owner, state)
    state.hand_size = 9; policy._cached_health(owner, state)
    assert health.calls == 2


def test_cache_invalidates_on_public_stateful_joker_field_change(monkeypatch):
    health = _CountingHealth(); monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace(); state = _state()
    policy._cached_health(owner, state); state.jokers[0].counter = 2; policy._cached_health(owner, state)
    assert health.calls == 2


def test_cache_invalidates_on_round_history_or_held_resource_change(monkeypatch):
    health = _CountingHealth(); monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace(); state = _state()
    policy._cached_health(owner, state)
    state.round_hand_play_counts["PAIR"] = 1; policy._cached_health(owner, state)
    state.consumables[0].used = True; policy._cached_health(owner, state)
    state.vouchers.append(SimpleNamespace(name="Palette")); policy._cached_health(owner, state)
    assert health.calls == 4
