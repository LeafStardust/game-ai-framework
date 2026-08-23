from __future__ import annotations

"""Let pinned candidate engines steer already-safe acquisition choices.

The original prescription adapter intentionally listened only to ACTIVE motifs.
That made strategy pursuit circular: the agent would not seek missing engine pieces
until the engine was already functioning.  This adapter broadens motif authority to
motifs carried by the canonical pinned strategy.  Existing pack/shop legality,
admission, survival and resource guards remain authoritative.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition


def install_pinned_strategy_execution_policy() -> None:
    import games.balatro.bond_prescription_policy as prescriptions

    if getattr(prescriptions, "_pinned_strategy_execution_installed", False):
        return

    original = prescriptions._active_motif_ids

    def strategy_motif_ids(state):
        result = set(original(state))
        try:
            _, composition = evaluate_bond_composition(state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return frozenset(result)

        pinned_id = getattr(composition, "pinned_strategy_id", None)
        if not pinned_id:
            return frozenset(result)
        for candidate in getattr(composition, "strategy_candidates", ()) or ():
            if candidate.strategy_id != pinned_id or not candidate.pinned:
                continue
            result.update(candidate.motif_ids)
            break
        return frozenset(result)

    prescriptions._active_motif_ids = strategy_motif_ids
    prescriptions._pinned_strategy_execution_installed = True
