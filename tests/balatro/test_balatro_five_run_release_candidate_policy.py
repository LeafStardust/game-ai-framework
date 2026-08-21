from types import SimpleNamespace

import pytest

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.five_run_release_candidate_policy import (
    _release_candidate_reroll_limit,
    roster_upgrade_pressure,
    shop_next_blind_floor,
)
from games.balatro.state import BalatroState
from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_phase_weight_policy import strategy_phase_weight


def _joker(name, **public_state):
    return SimpleNamespace(name=name, public_state=public_state)


def _state(*jokers, ante=5, money=30, slots=5):
    return SimpleNamespace(
        ante=ante,
        money=money,
        round_num=10,
        jokers=list(jokers),
        joker_slots=slots,
    )


def test_mixed_static_filler_full_roster_creates_upgrade_pressure():
    state = _state(
        _joker("Jolly Joker"),
        _joker("Abstract Joker"),
        _joker("Lusty Joker"),
        _joker("Crafty Joker"),
        _joker("Raised Fist"),
    )
    assert roster_upgrade_pressure(state) >= 3.0


def test_decay_jokers_get_weaker_as_realized_output_falls():
    weak = _state(
        _joker("Popcorn", mult=8),
        _joker("Ice Cream", chips=15),
        _joker("Abstract Joker"),
        _joker("Joker Stencil"),
        _joker("Sly Joker"),
    )
    developed = _state(
        _joker("Popcorn", mult=25),
        _joker("Ice Cream", chips=100),
        _joker("Ramen", x_mult=1.95),
        _joker("Obelisk", x_mult=2.0),
        _joker("Swashbuckler"),
    )
    assert roster_upgrade_pressure(weak) > roster_upgrade_pressure(developed)


def test_partial_roster_never_triggers_full_roster_pressure():
    state = _state(_joker("Abstract Joker"), _joker("Jolly Joker"), slots=5)
    assert roster_upgrade_pressure(state) == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("ante", "expected"),
    [(1, 300), (3, 2_000), (5, 11_000), (6, 20_000), (8, 50_000)],
)
def test_shop_next_blind_floor_uses_red_white_small_blind_requirement(ante, expected):
    state = SimpleNamespace(phase="SHOP", stake_name="WHITE", ante=ante)
    assert shop_next_blind_floor(state) == pytest.approx(expected)


def test_shop_build_health_no_longer_defaults_to_neutral_fifty_fifty_without_active_blind():
    state = BalatroState()
    state.phase = "SHOP"
    state.stake_name = "WHITE"
    state.ante = 5
    state.blind = None
    state.blind_score = 0
    state.jokers = []
    state.owned_deck = list(state.deck)

    health = RuntimeBuildHealthEvaluator().evaluate(state)

    # Ante-5 shop admission must be evaluated against an actual public blind floor,
    # not the previous no-target (50, 50) placeholder.
    assert (health.survival, health.immediate) != pytest.approx((50.0, 50.0))


def test_severely_weak_or_endangered_roster_gets_two_bounded_search_rolls():
    assert _release_candidate_reroll_limit(pressure=3.5, survival=80.0) == 2
    assert _release_candidate_reroll_limit(pressure=1.0, survival=60.0) == 2
    assert _release_candidate_reroll_limit(pressure=1.0, survival=80.0) == 1


@pytest.mark.parametrize(
    ("ante", "expected"),
    [(1, 0.25), (2, 0.25), (3, 0.50), (4, 0.70), (5, 0.90), (6, 1.00), (8, 1.00)],
)
def test_tracker_uses_one_authoritative_phase_pressure(ante, expected):
    tracker = BalatroStrategyTracker({})
    state = SimpleNamespace(ante=ante)
    assert strategy_phase_weight(ante) == pytest.approx(expected)
    assert tracker.strategy_pressure(state) == pytest.approx(expected)
