from __future__ import annotations

"""Canonical strategic value for realized Bond development.

This module converts already-evaluated, already-realized Bond development into a
numeric strategic value. It does not choose actions, mutate development, or
re-evaluate mechanics. Ranks remain diagnostic only.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from games.balatro.bonds.evaluation import evaluate_all_bonds
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


BOND_STRENGTH_EXPONENT = 1.35

REALIZATION_FACTORS: dict[BondRealization, float] = {
    BondRealization.DORMANT: 0.0,
    BondRealization.PARTIAL: 0.35,
    BondRealization.ACTIVE: 0.75,
    BondRealization.MATURE: 1.0,
}


@dataclass(frozen=True)
class BondStrategicValue:
    bond_id: str
    points: float
    strength: float
    realization: BondRealization
    realization_factor: float
    calibration_weight: float
    value: float
    rank: BondRank
    development: BondDevelopment


def bond_strength(points: float) -> float:
    """Return nonlinear development strength from non-negative Bond points."""
    return max(0.0, float(points)) ** BOND_STRENGTH_EXPONENT


def realization_factor(realization: BondRealization) -> float:
    try:
        return REALIZATION_FACTORS[BondRealization(realization)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Unknown Bond realization {realization!r}") from exc


def value_bond(
    development: BondDevelopment,
    *,
    calibration_weight: float = 1.0,
) -> BondStrategicValue:
    """Value one realized Bond without introducing action authority."""
    weight = float(calibration_weight)
    if weight < 0.0:
        raise ValueError("Bond calibration weight must be non-negative")

    points = max(0.0, float(development.contribution))
    strength = bond_strength(points)
    factor = realization_factor(development.realization)

    # Locked Bonds are strategically unavailable even if a malformed caller
    # supplies a non-dormant realization classification.
    if not development.unlocked or development.rank == BondRank.LOCKED:
        factor = 0.0

    value = strength * factor * weight
    return BondStrategicValue(
        bond_id=development.bond_id,
        points=points,
        strength=strength,
        realization=development.realization,
        realization_factor=factor,
        calibration_weight=weight,
        value=value,
        rank=development.rank,
        development=development,
    )


def value_developments(
    developments: tuple[BondDevelopment, ...],
    *,
    calibration_weights: Mapping[str, float] | None = None,
) -> tuple[BondStrategicValue, ...]:
    weights = calibration_weights or {}
    return tuple(
        value_bond(
            development,
            calibration_weight=float(weights.get(development.bond_id, 1.0)),
        )
        for development in developments
    )


def evaluate_bond_values(
    state: Any,
    *,
    calibration_weights: Mapping[str, float] | None = None,
) -> tuple[BondStrategicValue, ...]:
    """Evaluate public state through the canonical Bond pipeline and value it."""
    return value_developments(
        evaluate_all_bonds(state),
        calibration_weights=calibration_weights,
    )
