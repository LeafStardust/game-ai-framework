from __future__ import annotations

"""Canonical whole-build strategic value for Balatro.

BuildValue is intentionally a pure diagnostic/value layer. It evaluates the
supplied public state through canonical Bond, relationship, and exceptional
motif value paths. It does not project candidates or choose actions.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from games.balatro.bonds.motif_value import MotifValue, evaluate_motif_values
from games.balatro.bonds.relationships import RelationshipValue, value_relationships
from games.balatro.bonds.strategic_value import BondStrategicValue, evaluate_bond_values


@dataclass(frozen=True)
class BuildValue:
    bond_values: tuple[BondStrategicValue, ...]
    relationship_values: tuple[RelationshipValue, ...]
    motif_values: tuple[MotifValue, ...]
    bond_total: float
    relationship_total: float
    motif_total: float
    total: float

    @property
    def by_bond_id(self) -> dict[str, BondStrategicValue]:
        return {item.bond_id: item for item in self.bond_values}


def compose_build_value(
    bond_values: tuple[BondStrategicValue, ...],
    relationship_values: tuple[RelationshipValue, ...],
    motif_values: tuple[MotifValue, ...],
) -> BuildValue:
    """Compose already-evaluated strategic diagnostics into one scalar value."""
    bond_total = sum(item.value for item in bond_values)
    relationship_total = sum(item.value for item in relationship_values)
    motif_total = sum(item.value for item in motif_values)
    return BuildValue(
        bond_values=bond_values,
        relationship_values=relationship_values,
        motif_values=motif_values,
        bond_total=bond_total,
        relationship_total=relationship_total,
        motif_total=motif_total,
        total=bond_total + relationship_total + motif_total,
    )


def evaluate_build_value(
    state: Any,
    *,
    calibration_weights: Mapping[str, float] | None = None,
) -> BuildValue:
    """Return canonical BuildValue(state) with complete value diagnostics."""
    bonds = evaluate_bond_values(state, calibration_weights=calibration_weights)
    relationships = value_relationships(bonds)
    motifs = evaluate_motif_values(state, bonds)
    return compose_build_value(bonds, relationships, motifs)
