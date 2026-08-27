from types import SimpleNamespace

import games.balatro.live_competence_guard_policy as guards
from games.balatro.actions import DISCARD_CARDS, BalatroAction


def _card(*, seal=None):
    return SimpleNamespace(seal=seal)


def test_single_card_recovery_discard_is_dominated_without_precision_semantics():
    state = SimpleNamespace(hand=[_card(), _card(), _card()], jokers=[])
    assert guards._has_discard_precision_semantics(state) is False


def test_purple_seal_preserves_precision_discard_exception():
    state = SimpleNamespace(hand=[_card(seal="PURPLE"), _card()], jokers=[])
    assert guards._has_discard_precision_semantics(state) is True


def test_scaling_rescue_uses_existing_build_health_public_predicate(monkeypatch):
    health = SimpleNamespace(scaling_deficit=True)
    state = SimpleNamespace(ante=4, round=10, round_num=10, money=44)

    monkeypatch.setattr(guards.build_health_policy, "_cached_health", lambda owner, source: health)

    assert state.money - 5 >= 15
    assert health.scaling_deficit is True
