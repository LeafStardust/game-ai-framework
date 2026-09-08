from __future__ import annotations

"""Typed numerical calibration surface for the canonical Bond composer.

This module contains production defaults and a context-local override mechanism for
offline experiments. It deliberately has no Optuna dependency. Normal runtime
imports always see ``DEFAULT_BOND_CALIBRATION`` unless an offline evaluator enters
``use_bond_calibration`` explicitly.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from typing import Iterator, Mapping


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BondCalibration:
    """Numerical composer calibration for canonical structural Bond evidence."""

    realization_priority_weight: float = 0.75
    synergy_bonus: float = 1.50
    conflict_penalty: float = 2.00
    motif_potential_value: float = 1.00
    motif_active_value: float = 4.00
    motif_mature_value: float = 7.00

    def __post_init__(self) -> None:
        non_negative = (
            "realization_priority_weight",
            "synergy_bonus",
            "conflict_penalty",
            "motif_potential_value",
            "motif_active_value",
            "motif_mature_value",
        )
        for name in non_negative:
            value = float(getattr(self, name))
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative, got {value}")

        motif = (
            float(self.motif_potential_value),
            float(self.motif_active_value),
            float(self.motif_mature_value),
        )
        if not motif[0] <= motif[1] <= motif[2]:
            raise ValueError("motif values must satisfy POTENTIAL <= ACTIVE <= MATURE")

    def to_dict(self) -> dict[str, float | int]:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "BondCalibration":
        schema = int(values.get("schema_version", SCHEMA_VERSION))
        if schema != SCHEMA_VERSION:
            raise ValueError(f"unsupported Bond calibration schema {schema}; expected {SCHEMA_VERSION}")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(values) - allowed - {"schema_version"}
        if unknown:
            raise ValueError(f"unknown Bond calibration fields: {sorted(unknown)}")
        kwargs = {name: float(values[name]) for name in allowed if name in values}
        return cls(**kwargs)

    def with_overrides(self, **values: float) -> "BondCalibration":
        return replace(self, **values)


DEFAULT_BOND_CALIBRATION = BondCalibration()
_CURRENT_BOND_CALIBRATION: ContextVar[BondCalibration] = ContextVar(
    "balatro_bond_calibration",
    default=DEFAULT_BOND_CALIBRATION,
)


def current_bond_calibration() -> BondCalibration:
    return _CURRENT_BOND_CALIBRATION.get()


@contextmanager
def use_bond_calibration(calibration: BondCalibration) -> Iterator[BondCalibration]:
    """Temporarily apply one immutable calibration snapshot in this context."""
    if not isinstance(calibration, BondCalibration):
        raise TypeError("calibration must be a BondCalibration")
    token = _CURRENT_BOND_CALIBRATION.set(calibration)
    try:
        yield calibration
    finally:
        _CURRENT_BOND_CALIBRATION.reset(token)
