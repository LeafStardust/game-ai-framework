from __future__ import annotations

"""Deprecated compatibility shim for retired Bond prescription execution.

Phase H integrates exact persistent outcomes through canonical projected-state
StrategyDelta in their existing decision owners. Historical motif-specific
prescription bonuses must not post-process D9 pack choices or D14 consumable
utility after those owners have already received the canonical strategic signal.

The private motif-id helper remains temporarily for legacy diagnostic/test callers
that have not yet been migrated. It exposes composition state only and carries no
action-selection or prescription authority.
"""

from typing import Any

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.motifs import MotifState


def _active_motif_ids(state: Any) -> frozenset[str]:
    """Compatibility-only view of active public composition motifs."""
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return frozenset()
    return frozenset(
        str(motif.motif_id)
        for motif in tuple(getattr(composition, "motifs", ()) or ())
        if getattr(motif, "state", MotifState.ABSENT) >= MotifState.ACTIVE
    )


def install_bond_prescription_policy() -> None:
    """Compatibility no-op; manual Bond prescription execution is retired."""
    return None
