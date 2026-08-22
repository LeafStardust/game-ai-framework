from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, REALIZATION_STRENGTH, evaluate_motifs
from games.balatro.bonds.relationships import BondRelationship, relationship_between


@dataclass(frozen=True)
class Composition:
    bond_ids: tuple[str, ...]
    motifs: tuple[MotifEvaluation, ...]
    conflicts: tuple[tuple[str, str], ...]
    synergies: tuple[tuple[str, str], ...]
    coherence_score: float
    prescriptions: tuple[str, ...]



def _eligible(dev: BondDevelopment) -> bool:
    return dev.unlocked and dev.rank >= BondRank.R1


def _bond_priority(dev: BondDevelopment) -> float:
    # Structural/realization priority only. This is deliberately not score power.
    rank_weight = float(max(0, int(dev.rank)))
    realization_weight = float(REALIZATION_STRENGTH[dev.realization]) * 0.75
    return rank_weight + realization_weight


def compose_build(state: Any, developments: Iterable[BondDevelopment]) -> Composition:
    devs = [dev for dev in developments if _eligible(dev)]
    devs.sort(key=_bond_priority, reverse=True)

    selected: list[BondDevelopment] = []
    conflicts: list[tuple[str, str]] = []
    synergies: list[tuple[str, str]] = []

    for dev in devs:
        local_conflicts = [other for other in selected if relationship_between(dev.bond_id, other.bond_id) == BondRelationship.CONFLICT]
        if local_conflicts:
            strongest = max(local_conflicts, key=_bond_priority)
            if _bond_priority(dev) <= _bond_priority(strongest):
                conflicts.append((dev.bond_id, strongest.bond_id))
                continue
            selected = [other for other in selected if other not in local_conflicts]
            conflicts.extend((other.bond_id, dev.bond_id) for other in local_conflicts)
        selected.append(dev)

    selected_ids = {dev.bond_id for dev in selected}
    for i, left in enumerate(selected):
        for right in selected[i + 1:]:
            if relationship_between(left.bond_id, right.bond_id) == BondRelationship.SYNERGY:
                synergies.append((left.bond_id, right.bond_id))

    motifs = tuple(m for m in evaluate_motifs(state, selected) if m.state != MotifState.ABSENT)

    # Coherence is a planning score, not projected chips. It rewards realized,
    # mutually supportive structure and motif completion while penalizing unresolved conflicts.
    base = sum(_bond_priority(dev) for dev in selected)
    synergy_bonus = 1.5 * len(synergies)
    motif_bonus = sum({MotifState.POTENTIAL: 1.0, MotifState.ACTIVE: 4.0, MotifState.MATURE: 7.0}.get(m.state, 0.0) for m in motifs)
    conflict_penalty = 2.0 * len(conflicts)
    coherence = base + synergy_bonus + motif_bonus - conflict_penalty

    prescriptions: list[str] = []
    for motif in motifs:
        if motif.state >= MotifState.ACTIVE:
            prescriptions.extend(motif.prescriptions)
    prescriptions = list(dict.fromkeys(prescriptions))

    return Composition(
        bond_ids=tuple(dev.bond_id for dev in selected),
        motifs=motifs,
        conflicts=tuple(conflicts),
        synergies=tuple(synergies),
        coherence_score=coherence,
        prescriptions=tuple(prescriptions),
    )
