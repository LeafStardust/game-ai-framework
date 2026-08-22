from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any

from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, REALIZATION_STRENGTH, evaluate_motifs
from games.balatro.bonds.relationships import BondRelationship, relationship_between


@dataclass(frozen=True)
class Composition:
    bond_ids: tuple[str, ...]
    motifs: tuple[MotifEvaluation, ...]
    conflicts: tuple[tuple[str, str], ...]
    synergies: tuple[tuple[str, str], ...]
    coherence_score: float
    pivot_resistance: float
    motif_distance: tuple[tuple[str, int], ...]
    prescriptions: tuple[str, ...]


def _eligible(dev: BondDevelopment) -> bool:
    return dev.unlocked and dev.rank >= BondRank.R1


def _bond_priority(dev: BondDevelopment) -> float:
    rank_weight=float(max(0,int(dev.rank)))
    realization_weight=float(REALIZATION_STRENGTH[dev.realization])*0.75
    return rank_weight+realization_weight


def _pivot_resistance(dev: BondDevelopment) -> float:
    # Cost of abandoning established structure; never a lock.
    return {BondRank.R1:0.5,BondRank.R2:1.0,BondRank.R3:2.5,BondRank.R4:4.5,BondRank.R5:7.0}.get(dev.rank,0.0)


def compose_build(state: Any, developments: Iterable[BondDevelopment]) -> Composition:
    devs=[dev for dev in developments if _eligible(dev)]
    devs.sort(key=lambda d: (_bond_priority(d), _pivot_resistance(d)), reverse=True)

    selected:list[BondDevelopment]=[]; conflicts:list[tuple[str,str]]=[]
    for dev in devs:
        local=[other for other in selected if relationship_between(dev.bond_id,other.bond_id)==BondRelationship.CONFLICT]
        if not local:
            selected.append(dev); continue
        challenger=(_bond_priority(dev)+0.20*_pivot_resistance(dev))
        incumbents=max((_bond_priority(o)+0.20*_pivot_resistance(o) for o in local),default=0.0)
        if challenger<=incumbents:
            conflicts.extend((dev.bond_id,o.bond_id) for o in local);continue
        conflicts.extend((o.bond_id,dev.bond_id) for o in local)
        selected=[o for o in selected if o not in local];selected.append(dev)

    synergies:set[tuple[str,str]]=set()
    for i,left in enumerate(selected):
        for right in selected[i+1:]:
            if relationship_between(left.bond_id,right.bond_id)==BondRelationship.SYNERGY:
                synergies.add(tuple(sorted((left.bond_id,right.bond_id))))

    motifs=tuple(m for m in evaluate_motifs(state,selected) if m.state!=MotifState.ABSENT)
    base=sum(_bond_priority(dev) for dev in selected)
    synergy_bonus=1.5*len(synergies)
    motif_bonus=sum({MotifState.POTENTIAL:1.0,MotifState.ACTIVE:4.0,MotifState.MATURE:7.0}.get(m.state,0.0) for m in motifs)
    conflict_penalty=2.0*len(set(tuple(sorted(c)) for c in conflicts))
    coherence=base+synergy_bonus+motif_bonus-conflict_penalty

    prescriptions:list[str]=[]
    for motif in motifs:
        if motif.state>=MotifState.ACTIVE: prescriptions.extend(motif.prescriptions)
    prescriptions=list(dict.fromkeys(prescriptions))

    return Composition(
        bond_ids=tuple(dev.bond_id for dev in selected),
        motifs=motifs,
        conflicts=tuple(dict.fromkeys(conflicts)),
        synergies=tuple(sorted(synergies)),
        coherence_score=coherence,
        pivot_resistance=sum(_pivot_resistance(dev) for dev in selected),
        motif_distance=tuple((m.motif_id,m.missing_count) for m in motifs),
        prescriptions=tuple(prescriptions),
    )
