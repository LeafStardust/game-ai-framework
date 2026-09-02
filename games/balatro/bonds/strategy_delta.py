from __future__ import annotations

"""Canonical projected whole-build strategic delta.

This layer compares two already-valid public states. It does not own candidate
simulation, legality, affordability, survival, boss rules, or action selection.
Decision owners may supply their own projector through ``strategy_delta``.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from games.balatro.bonds.build_value import BuildValue, evaluate_build_value


DEFAULT_TRANSITION_COST_FRACTION = 0.05


@dataclass(frozen=True)
class StrategyDelta:
    current: BuildValue
    projected: BuildValue
    raw_delta: float
    removed_realized_structure: float
    transition_cost_fraction: float
    transition_cost: float
    value: float


StateProjector = Callable[[Any, Any], Any]


def removed_realized_structure(current: BuildValue, projected: BuildValue) -> float:
    """Return Bond value removed by the projected state.

    This is intentionally Bond-local rather than a named-strategy commitment
    score. Relationship and motif losses already appear in ``raw_delta`` and are
    not charged again as transition inertia.
    """
    current_by_id = current.by_bond_id
    projected_by_id = projected.by_bond_id
    return sum(
        max(0.0, item.value - projected_by_id.get(bond_id, item).value)
        for bond_id, item in current_by_id.items()
    )


def strategy_delta_from_build_values(
    current: BuildValue,
    projected: BuildValue,
    *,
    transition_cost_fraction: float = DEFAULT_TRANSITION_COST_FRACTION,
) -> StrategyDelta:
    fraction = float(transition_cost_fraction)
    if fraction < 0.0:
        raise ValueError("transition cost fraction must be non-negative")

    raw_delta = projected.total - current.total
    removed = removed_realized_structure(current, projected)
    cost = removed * fraction
    return StrategyDelta(
        current=current,
        projected=projected,
        raw_delta=raw_delta,
        removed_realized_structure=removed,
        transition_cost_fraction=fraction,
        transition_cost=cost,
        value=raw_delta - cost,
    )


def strategy_delta_from_states(
    state: Any,
    projected_state: Any,
    *,
    calibration_weights: Mapping[str, float] | None = None,
    transition_cost_fraction: float = DEFAULT_TRANSITION_COST_FRACTION,
) -> StrategyDelta:
    """Compare canonical BuildValue for current and projected public states."""
    current = evaluate_build_value(state, calibration_weights=calibration_weights)
    projected = evaluate_build_value(projected_state, calibration_weights=calibration_weights)
    return strategy_delta_from_build_values(
        current,
        projected,
        transition_cost_fraction=transition_cost_fraction,
    )


def strategy_delta(
    candidate: Any,
    state: Any,
    *,
    projector: StateProjector,
    calibration_weights: Mapping[str, float] | None = None,
    transition_cost_fraction: float = DEFAULT_TRANSITION_COST_FRACTION,
) -> StrategyDelta:
    """Project one candidate with the caller's canonical domain projector."""
    projected_state = projector(state, candidate)
    return strategy_delta_from_states(
        state,
        projected_state,
        calibration_weights=calibration_weights,
        transition_cost_fraction=transition_cost_fraction,
    )
