from types import SimpleNamespace

import pytest

from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_phase_weight_policy import (
    strategy_phase_name,
    strategy_phase_weight,
)
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


@pytest.mark.parametrize(
    ("ante", "expected"),
    [
        (1, 0.25),
        (2, 0.25),
        (3, 0.50),
        (4, 0.70),
        (5, 0.90),
        (6, 1.00),
        (8, 1.00),
    ],
)
def test_strategy_pressure_ramps_by_ante(ante, expected):
    assert strategy_phase_weight(ante) == pytest.approx(expected)


def test_strategy_phase_names_match_run_lifecycle():
    assert strategy_phase_name(1) == "FOUNDATION"
    assert strategy_phase_name(2) == "FOUNDATION"
    assert strategy_phase_name(3) == "FORMATION"
    assert strategy_phase_name(5) == "FORMATION"
    assert strategy_phase_name(6) == "COMMITMENT"
    assert strategy_phase_name(8) == "COMMITMENT"


def test_foundation_phase_keeps_scoring_probes_broad():
    evaluator = object.__new__(StrategyAwareJokerBuildValueEvaluator)
    assert evaluator._active_probe_hands(SimpleNamespace(ante=1)) == ()
    assert evaluator._active_probe_hands(SimpleNamespace(ante=2)) == ()


def test_foundation_strategy_scope_decays_after_top_three_routes():
    tracker = BalatroStrategyTracker({})
    state = SimpleNamespace(ante=1)
    resolution = SimpleNamespace(dominant_strategy_id="first")

    assert tracker._scope_factor(state, "first", 0, resolution) == pytest.approx(1.0)
    assert tracker._scope_factor(state, "second", 1, resolution) == pytest.approx(0.5)
    assert tracker._scope_factor(state, "third", 2, resolution) == pytest.approx(0.25)
    assert tracker._scope_factor(state, "fourth", 3, resolution) == pytest.approx(0.0)
