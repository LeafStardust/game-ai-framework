from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from games.balatro.bonds.calibration import current_bond_calibration
from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, REALIZATION_STRENGTH, evaluate_motifs
from games.balatro.bonds.relationships import BondRelationship, relationship_between


@dataclass(frozen=True)
class Composition:
    """Structural Bond composition only.

    Named strategy identities, commitment states, StrategyPlan objects and action
    prescriptions were part of the retired strategy-controller architecture. The
    canonical composer exposes only mechanical Bond selection, sparse relationships,
    exceptional motifs and aggregate structural diagnostics.
    """

    bond_ids: tuple[str, ...]
    motifs: tuple[MotifEvaluation, ...]
    conflicts: tuple[tuple[str, str], ...]
    synergies: tuple[tuple[str, str], ...]
    coherence_score: float
    pivot_resistance: float
    motif_distance: tuple[tuple[str, int], ...]


# Exceptional motifs may expose POTENTIAL once a genuinely defining component is
# present. This is motif evidence only; it does not create a strategy identity,
# commitment state, plan, or recruitment prescription.
_DEFINING_MOTIF_CORES: dict[str, frozenset[str]] = {
    "baron_mime_steel": frozenset({"BARON", "MIME"}),
    "photograph_hanging_chad": frozenset({"PHOTOGRAPH", "HANGING_CHAD"}),
    # Midas Mask has a complete independent Gold-economy use and therefore does
    # not, by itself, imply Vampire. Vampire is the defining payoff that turns
    # Midas into renewable enhancement feed.
    "vampire_midas": frozenset({"VAMPIRE"}),
    "burnt_target_level": frozenset({"BURNT_JOKER"}),
    "low_rank_hack_retrigger": frozenset({"HACK"}),
}


def _eligible(dev: BondDevelopment) -> bool:
    return dev.unlocked and dev.rank >= BondRank.R1


def _bond_priority(dev: BondDevelopment) -> float:
    calibration = current_bond_calibration()
    return float(max(0, int(dev.rank))) + (
        float(REALIZATION_STRENGTH[dev.realization]) * calibration.realization_priority_weight
    )


def _pivot_resistance(dev: BondDevelopment) -> float:
    return current_bond_calibration().pivot_resistance(dev.rank)


def _component_token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _single_core_motif(motif: MotifEvaluation) -> MotifEvaluation | None:
    if len(tuple(motif.present_components or ())) != 1:
        return None
    defining = {
        _component_token(value)
        for value in _DEFINING_MOTIF_CORES.get(str(motif.motif_id), frozenset())
    }
    if not defining:
        return None
    present = {_component_token(value) for value in tuple(motif.present_components or ())}
    if not defining.intersection(present):
        return None
    if motif.state == MotifState.ABSENT:
        return replace(motif, state=MotifState.POTENTIAL)
    return motif


def compose_build(state: Any, developments: Iterable[BondDevelopment]) -> Composition:
    """Compose canonical structural Bond evidence from realized developments."""
    calibration = current_bond_calibration()
    all_developments = tuple(developments)
    devs = [dev for dev in all_developments if _eligible(dev)]
    devs.sort(key=lambda d: (_bond_priority(d), _pivot_resistance(d)), reverse=True)

    selected: list[BondDevelopment] = []
    conflicts: list[tuple[str, str]] = []
    for dev in devs:
        local = [
            other
            for other in selected
            if relationship_between(dev.bond_id, other.bond_id) == BondRelationship.CONFLICT
        ]
        if not local:
            selected.append(dev)
            continue
        challenger = _bond_priority(dev) + 0.20 * _pivot_resistance(dev)
        incumbents = max(
            (_bond_priority(other) + 0.20 * _pivot_resistance(other) for other in local),
            default=0.0,
        )
        if challenger <= incumbents:
            conflicts.extend((dev.bond_id, other.bond_id) for other in local)
            continue
        conflicts.extend((other.bond_id, dev.bond_id) for other in local)
        selected = [other for other in selected if other not in local]
        selected.append(dev)

    synergies: set[tuple[str, str]] = set()
    for index, left in enumerate(selected):
        for right in selected[index + 1 :]:
            if relationship_between(left.bond_id, right.bond_id) == BondRelationship.SYNERGY:
                synergies.add(tuple(sorted((left.bond_id, right.bond_id))))

    raw_motifs = tuple(evaluate_motifs(state, all_developments))
    motifs_list: list[MotifEvaluation] = []
    for motif in raw_motifs:
        promoted = _single_core_motif(motif)
        if motif.state != MotifState.ABSENT:
            motifs_list.append(motif)
        elif promoted is not None:
            motifs_list.append(promoted)
    motifs = tuple(motifs_list)

    base = sum(_bond_priority(dev) for dev in selected)
    synergy_bonus = calibration.synergy_bonus * len(synergies)
    motif_values = {
        MotifState.POTENTIAL: calibration.motif_potential_value,
        MotifState.ACTIVE: calibration.motif_active_value,
        MotifState.MATURE: calibration.motif_mature_value,
    }
    motif_bonus = sum(motif_values.get(motif.state, 0.0) for motif in motifs)
    conflict_penalty = calibration.conflict_penalty * len(
        set(tuple(sorted(conflict)) for conflict in conflicts)
    )
    coherence = base + synergy_bonus + motif_bonus - conflict_penalty

    return Composition(
        bond_ids=tuple(dev.bond_id for dev in selected),
        motifs=motifs,
        conflicts=tuple(dict.fromkeys(conflicts)),
        synergies=tuple(sorted(synergies)),
        coherence_score=coherence,
        pivot_resistance=sum(_pivot_resistance(dev) for dev in selected),
        motif_distance=tuple((motif.motif_id, motif.missing_count) for motif in motifs),
    )
