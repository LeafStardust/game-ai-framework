from __future__ import annotations

from typing import Any, Callable

from games.balatro.bonds.ids import BOND_IDS, LEGACY_BOND_ID_ALIASES
from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.realization_held import HELD_REALIZERS
from games.balatro.bonds.realization_common import COMMON_REALIZERS
from games.balatro.bonds.realization_rank_state import RANK_STATE_REALIZERS
from games.balatro.bonds.realization_engine import ENGINE_REALIZERS
from games.balatro.bonds.realization_advanced import ADVANCED_REALIZERS
from games.balatro.bonds.realization_engine_order_audit import ENGINE_AUDIT_REALIZERS
from games.balatro.bonds.realization_engine_triggered import TRIGGERED_ENGINE_OVERRIDES
from games.balatro.bonds.realization_engine_liveness_audit import ENGINE_LIVENESS_AUDIT_REALIZERS
from games.balatro.bonds.realization_contract_compat import CONTRACT_COMPAT_REALIZERS
from games.balatro.bonds.realization_canonical import CANONICAL_REALIZERS

Realizer = Callable[[BondDevelopment, Any], BondDevelopment]

REALIZERS: dict[str, Realizer] = {}
for family in (HELD_REALIZERS, COMMON_REALIZERS, RANK_STATE_REALIZERS, ENGINE_REALIZERS, ADVANCED_REALIZERS):
    overlap = set(REALIZERS).intersection(family)
    if overlap:
        raise RuntimeError(f"Duplicate Bond realizer registration: {sorted(overlap)}")
    REALIZERS.update(family)

REALIZERS.update(ENGINE_AUDIT_REALIZERS)
REALIZERS.update(TRIGGERED_ENGINE_OVERRIDES)
REALIZERS.update(ENGINE_LIVENESS_AUDIT_REALIZERS)
REALIZERS.update(CONTRACT_COMPAT_REALIZERS)

# Remove legacy strategic IDs from the production registry. The old realizer
# implementations remain temporarily as mechanic/reference code until cleanup.
for legacy_id in LEGACY_BOND_ID_ALIASES:
    REALIZERS.pop(legacy_id, None)

# Canonical axis-level realization is authoritative for renamed Bonds.
REALIZERS.update(CANONICAL_REALIZERS)

# Compatibility export used by existing tests/callers. The source of truth is ids.py.
FROZEN_BOND_IDS = BOND_IDS


def missing_realizers() -> tuple[str, ...]:
    return tuple(sorted(set(FROZEN_BOND_IDS) - set(REALIZERS)))


def extra_realizers() -> tuple[str, ...]:
    return tuple(sorted(set(REALIZERS) - set(FROZEN_BOND_IDS)))


def realize_bond(dev: BondDevelopment, state: Any) -> BondDevelopment:
    try:
        fn = REALIZERS[dev.bond_id]
    except KeyError as exc:
        raise KeyError(f"No Realizer registered for Bond {dev.bond_id!r}") from exc
    result = fn(dev, state)
    if result.rank != dev.rank:
        raise AssertionError(f"Realizer mutated rank for {dev.bond_id}: {dev.rank} -> {result.rank}")
    if result.contribution != dev.contribution:
        raise AssertionError(
            f"Realizer mutated contribution for {dev.bond_id}: {dev.contribution} -> {result.contribution}"
        )
    return result
