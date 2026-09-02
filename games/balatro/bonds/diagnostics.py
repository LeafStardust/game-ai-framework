from __future__ import annotations

from typing import Any

from games.balatro.bonds.evaluation import evaluate_bond_structure
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


_REALIZATION_WEIGHT = {
    BondRealization.DORMANT: 0.0,
    BondRealization.PARTIAL: 0.5,
    BondRealization.ACTIVE: 1.0,
    BondRealization.MATURE: 1.5,
}


def _bond_priority(development: BondDevelopment) -> tuple[float, float, float, str]:
    return (
        float(max(0, int(development.rank))) + _REALIZATION_WEIGHT[development.realization],
        float(development.contribution),
        -float(development.points_to_next_rank or 0.0),
        development.bond_id,
    )


def _bond_payload(development: BondDevelopment) -> dict[str, Any]:
    return {
        "bond_id": development.bond_id,
        "target": development.target,
        "rank": development.rank.name,
        "rank_value": int(development.rank),
        "contribution": float(development.contribution),
        "next_rank_threshold": (
            float(development.next_rank_threshold)
            if development.next_rank_threshold is not None
            else None
        ),
        "points_to_next_rank": (
            float(development.points_to_next_rank)
            if development.points_to_next_rank is not None
            else None
        ),
        "realization": development.realization.value,
        "contributors": [
            {
                "source": contribution.source,
                "value": float(contribution.value),
                "roles": [role.value for role in contribution.roles],
                "targets": list(contribution.targets),
                "conditions": list(contribution.conditions),
            }
            for contribution in development.contributions
        ],
    }


def bond_strategy_diagnostics(state: Any) -> dict[str, Any]:
    """Return operator-facing canonical Bond/composition telemetry.

    The function name is retained as a logging-schema compatibility surface. Its
    payload is structural only: no named strategy identity, commitment state,
    StrategyPlan or action prescription is reconstructed for diagnostics.
    """
    developments, composition = evaluate_bond_structure(state)
    by_id = {development.bond_id: development for development in developments}
    relevant = [
        by_id[bond_id]
        for bond_id in composition.bond_ids
        if bond_id in by_id and by_id[bond_id].rank >= BondRank.R1
    ]
    relevant.sort(key=_bond_priority, reverse=True)

    motifs = [
        {
            "motif_id": motif.motif_id,
            "state": motif.state.name,
            "missing_count": int(motif.missing_count),
            "relevant_bonds": list(motif.relevant_bonds),
            "present_components": list(motif.present_components),
            "missing_components": list(motif.missing_components),
        }
        for motif in composition.motifs
    ]

    return {
        "power_engine": relevant[0].bond_id if relevant else None,
        "relevant_bonds": [_bond_payload(development) for development in relevant],
        "composition": {
            "bond_ids": list(composition.bond_ids),
            "motifs": motifs,
            "conflicts": [list(pair) for pair in composition.conflicts],
            "synergies": [list(pair) for pair in composition.synergies],
            "coherence_score": float(composition.coherence_score),
            "pivot_resistance": float(composition.pivot_resistance),
            "motif_distance": [list(item) for item in composition.motif_distance],
        },
    }
