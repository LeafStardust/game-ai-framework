from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from games.balatro.bonds.calibration import current_bond_calibration
from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, REALIZATION_STRENGTH, evaluate_motifs
from games.balatro.bonds.relationships import BondRelationship, relationship_between
from games.balatro.bonds.strategy_semantics import StrategyCandidate, form_strategy_candidates, pinned_strategy


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
    strategy_candidates: tuple[StrategyCandidate, ...] = ()
    pinned_strategy_id: str | None = None


def _eligible(dev: BondDevelopment) -> bool:
    # Rank still determines established Bond authority.  Strategy formation itself
    # deliberately happens from all positive mechanical evidence in
    # strategy_semantics, so R0 is not strategically invisible anymore.
    return dev.unlocked and dev.rank >= BondRank.R1


def _bond_priority(dev: BondDevelopment) -> float:
    calibration = current_bond_calibration()
    rank_weight = float(max(0, int(dev.rank)))
    realization_weight = (
        float(REALIZATION_STRENGTH[dev.realization])
        * calibration.realization_priority_weight
    )
    return rank_weight + realization_weight


def _pivot_resistance(dev: BondDevelopment) -> float:
    # Cost of abandoning established structure; never a lock.
    return current_bond_calibration().pivot_resistance(dev.rank)


def compose_build(state: Any, developments: Iterable[BondDevelopment]) -> Composition:
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

    # Motifs are observations about the public build, not rewards that should vanish
    # just because a supporting Bond has not crossed R1 yet.  Evaluate against the
    # full catalogue so incomplete engines can be noticed while they are still being
    # formed.
    motifs = tuple(
        motif
        for motif in evaluate_motifs(state, all_developments)
        if motif.state != MotifState.ABSENT
    )
    candidates = form_strategy_candidates(all_developments, motifs)
    pinned = pinned_strategy(candidates)

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

    prescriptions: list[str] = []
    for motif in motifs:
        if motif.state >= MotifState.ACTIVE:
            prescriptions.extend(motif.prescriptions)
    # A pinned candidate is already a strategic commitment.  Its prescriptions are
    # allowed to steer safe choices before the engine is fully realized; legality,
    # survival and family-specific admission policies remain authoritative below it.
    if pinned is not None:
        prescriptions.extend(pinned.prescriptions)
    prescriptions = list(dict.fromkeys(prescriptions))

    return Composition(
        bond_ids=tuple(dev.bond_id for dev in selected),
        motifs=motifs,
        conflicts=tuple(dict.fromkeys(conflicts)),
        synergies=tuple(sorted(synergies)),
        coherence_score=coherence,
        pivot_resistance=sum(_pivot_resistance(dev) for dev in selected),
        motif_distance=tuple((motif.motif_id, motif.missing_count) for motif in motifs),
        prescriptions=tuple(prescriptions),
        strategy_candidates=candidates,
        pinned_strategy_id=None if pinned is None else pinned.strategy_id,
    )
