from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from games.balatro.bonds.behavior_strategy import form_behavior_strategy_candidates, merge_strategy_candidates
from games.balatro.bonds.calibration import current_bond_calibration
from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.motifs import MotifEvaluation, MotifState, REALIZATION_STRENGTH, evaluate_motifs
from games.balatro.bonds.relationships import BondRelationship, relationship_between
from games.balatro.bonds.strategy_plan import StrategyPlan, build_strategy_plan
from games.balatro.bonds.strategy_semantics import (
    StrategyCandidate,
    StrategyCommitment,
    form_strategy_candidates,
    pinned_strategy,
)


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
    strategy_plan: StrategyPlan | None = None


_SUIT_BONDS = frozenset({"clubs", "diamonds", "hearts", "spades"})


def _eligible(dev: BondDevelopment) -> bool:
    # Rank still determines established Bond authority. Strategy formation happens
    # independently from all positive mechanical evidence, so R0 is not invisible.
    return dev.unlocked and dev.rank >= BondRank.R1


def _bond_priority(dev: BondDevelopment) -> float:
    calibration = current_bond_calibration()
    return float(max(0, int(dev.rank))) + (
        float(REALIZATION_STRENGTH[dev.realization]) * calibration.realization_priority_weight
    )


def _pivot_resistance(dev: BondDevelopment) -> float:
    return current_bond_calibration().pivot_resistance(dev.rank)


def _sanitize_behavior_candidates(
    candidates: Iterable[StrategyCandidate],
) -> tuple[StrategyCandidate, ...]:
    """Reject generic behavior graphs that are not actionable strategies."""
    result: list[StrategyCandidate] = []
    for candidate in candidates:
        suit_count = len(_SUIT_BONDS.intersection(candidate.bond_ids))
        if not candidate.motif_ids and suit_count > 1:
            continue

        concrete_sources = tuple(
            source for source in candidate.sources
            if not str(source).lower().startswith("feature:")
        )
        if (
            not candidate.motif_ids
            and len(candidate.bond_ids) == 1
            and len(set(concrete_sources)) < 2
            and candidate.commitment >= StrategyCommitment.PINNED
        ):
            candidate = replace(candidate, commitment=StrategyCommitment.FORMING)
        result.append(candidate)
    return tuple(result)


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

    motifs = tuple(
        motif
        for motif in evaluate_motifs(state, all_developments)
        if motif.state != MotifState.ABSENT
    )
    role_candidates = form_strategy_candidates(all_developments, motifs)
    try:
        behavior_candidates = _sanitize_behavior_candidates(
            form_behavior_strategy_candidates(state, all_developments, motifs)
        )
    except (AttributeError, TypeError, ValueError):
        behavior_candidates = ()
    candidates = merge_strategy_candidates(role_candidates, behavior_candidates)
    pinned = pinned_strategy(candidates)
    plan = build_strategy_plan(pinned, all_developments, motifs)

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
    if plan is not None:
        prescriptions.extend(plan.prescriptions)
    elif pinned is not None:
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
        strategy_plan=plan,
    )
