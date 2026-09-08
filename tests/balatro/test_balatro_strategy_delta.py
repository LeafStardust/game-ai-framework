from types import SimpleNamespace

import games.balatro.bonds.strategy_delta as delta_module
from games.balatro.bonds.build_value import compose_build_value
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.strategic_value import value_bond
from games.balatro.bonds.strategy_delta import (
    DEFAULT_TRANSITION_COST_FRACTION,
    strategy_delta,
    strategy_delta_from_build_values,
)


def _bond(bond_id: str, points: float):
    return value_bond(
        BondDevelopment(
            bond_id=bond_id,
            unlocked=True,
            contribution=points,
            rank=BondRank.R2,
            next_rank_threshold=None,
            contributions=(),
            realization=BondRealization.ACTIVE,
        )
    )


def _build(*bonds):
    return compose_build_value(tuple(bonds), (), ())


def test_strategy_delta_is_projected_minus_current_when_nothing_is_removed():
    current = _build(_bond("pair", 8.0))
    projected = _build(_bond("pair", 10.0))
    result = strategy_delta_from_build_values(current, projected)

    assert result.raw_delta == projected.total - current.total
    assert result.removed_realized_structure == 0.0
    assert result.transition_cost == 0.0
    assert result.value == result.raw_delta
    assert result.value > 0.0


def test_removing_realized_structure_adds_only_small_transition_inertia():
    current = _build(_bond("held_cards", 16.0), _bond("steel", 10.0))
    projected = _build(_bond("held_cards", 16.0), _bond("steel", 4.0))
    result = strategy_delta_from_build_values(current, projected)

    removed = current.by_bond_id["steel"].value - projected.by_bond_id["steel"].value
    assert result.removed_realized_structure == removed
    assert result.transition_cost == removed * DEFAULT_TRANSITION_COST_FRACTION
    assert result.value == result.raw_delta - result.transition_cost
    assert result.transition_cost > 0.0


def test_materially_stronger_alternative_can_overcome_transition_cost():
    current = _build(_bond("held_cards", 14.0), _bond("steel", 10.0))
    projected = _build(_bond("cash", 28.0))
    result = strategy_delta_from_build_values(current, projected)

    assert result.removed_realized_structure > 0.0
    assert result.transition_cost > 0.0
    assert result.value > 0.0


def test_transition_cost_does_not_create_named_strategy_state():
    current = _build(_bond("pair", 8.0))
    projected = _build(_bond("pair", 8.0))
    result = strategy_delta_from_build_values(current, projected)

    assert result.value == 0.0
    assert not hasattr(result, "strategy")
    assert not hasattr(result, "pivot_state")
    assert not hasattr(result, "commitment")


def test_negative_transition_cost_fraction_is_rejected():
    current = _build(_bond("pair", 8.0))
    try:
        strategy_delta_from_build_values(current, current, transition_cost_fraction=-0.01)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative transition cost should fail")


def test_candidate_adapter_uses_caller_owned_projector(monkeypatch):
    state = SimpleNamespace(value="current")
    projected_state = SimpleNamespace(value="projected")
    candidate = object()
    current_build = _build(_bond("pair", 8.0))
    projected_build = _build(_bond("pair", 10.0))
    calls = []

    def projector(received_state, received_candidate):
        calls.append((received_state, received_candidate))
        return projected_state

    def fake_evaluate_build_value(received_state, *, calibration_weights=None):
        assert calibration_weights is None
        if received_state is state:
            return current_build
        assert received_state is projected_state
        return projected_build

    monkeypatch.setattr(delta_module, "evaluate_build_value", fake_evaluate_build_value)
    result = strategy_delta(candidate, state, projector=projector)

    assert calls == [(state, candidate)]
    assert result.current is current_build
    assert result.projected is projected_build
    assert result.value > 0.0
