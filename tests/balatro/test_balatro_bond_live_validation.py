from types import SimpleNamespace

from games.balatro.bond_shop_health_policy import (
    StrategyHealthProvenance,
    clear_strategy_health,
    last_strategy_health,
)
from games.balatro.live.strategy_health import StrategyHealthMode
from games.balatro.state import BalatroState


def _state():
    state = BalatroState()
    state.phase = "SHOP"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 3
    state.round = 5
    state.owned_deck = list(state.deck)
    return state


def test_shop_health_cache_rejects_unrelated_round_or_run_identity(monkeypatch):
    import games.balatro.bond_shop_health_policy as policy

    matching = _state()
    health = SimpleNamespace(mode=StrategyHealthMode.REPAIR)
    monkeypatch.setattr(policy, "_LAST_STRATEGY_HEALTH", health)
    monkeypatch.setattr(
        policy,
        "_LAST_STRATEGY_HEALTH_PROVENANCE",
        StrategyHealthProvenance("RED", "WHITE", 3, 5),
    )
    assert last_strategy_health(matching) is health

    different_round = _state()
    different_round.round = 6
    assert last_strategy_health(different_round) is None

    different_deck = _state()
    different_deck.deck_name = "BLUE"
    assert last_strategy_health(different_deck) is None


def test_clear_strategy_health_removes_cached_authority(monkeypatch):
    import games.balatro.bond_shop_health_policy as policy

    monkeypatch.setattr(policy, "_LAST_STRATEGY_HEALTH", SimpleNamespace(mode=StrategyHealthMode.SURVIVE))
    monkeypatch.setattr(
        policy,
        "_LAST_STRATEGY_HEALTH_PROVENANCE",
        StrategyHealthProvenance("RED", "WHITE", 2, 4),
    )
    clear_strategy_health()
    assert policy._LAST_STRATEGY_HEALTH is None
    assert policy._LAST_STRATEGY_HEALTH_PROVENANCE is None
