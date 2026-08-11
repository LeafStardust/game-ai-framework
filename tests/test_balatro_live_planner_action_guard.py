from dataclasses import dataclass

from games.balatro.live.external.blind_clear_planner_action_live_validation import (
    _is_guaranteed,
    _probabilistic_guard_passes,
)


@dataclass
class _Value:
    clear_probability: float


@dataclass
class _Plan:
    exact: bool
    value: _Value


def test_exact_guaranteed_guard_requires_exact_probability_one():
    assert _is_guaranteed(_Plan(True, _Value(1.0))) is True
    assert _is_guaranteed(_Plan(False, _Value(1.0))) is False
    assert _is_guaranteed(_Plan(True, _Value(0.99))) is False


def test_probabilistic_guard_requires_explicit_threshold():
    plan = _Plan(False, _Value(0.890625))

    assert _probabilistic_guard_passes(plan, None) is False
    assert _probabilistic_guard_passes(plan, 0.90) is False
    assert _probabilistic_guard_passes(plan, 0.85) is True
    assert _probabilistic_guard_passes(plan, 0.890625) is True
