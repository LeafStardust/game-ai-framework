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
_HAND_BONDS = frozenset(
    {
        "high_card",
        "pair",
        "two_pair",
        "three_kind",
        "four_kind",
        "straight",
        "flush",
        "full_house",
        "straight_flush",
        "five_kind",
        "flush_house",
        "flush_five",
    }
)

# A known strategy becomes trackable from its first defining piece, but that does
# not grant PINNED authority. This belongs in the canonical composer so callers that
# import compose_build directly receive the same behavior as production wrappers.
_DEFINING_MOTIF_CORES: dict[str, frozenset[str]] = {
    "baron_mime_steel": frozenset({"BARON", "MIME"}),
    "photograph_hanging_chad": frozenset({"PHOTOGRAPH", "HANGING_CHAD"}),
    "vampire_midas": frozenset({"VAMPIRE", "MIDAS_MASK"}),
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


def _sanitize_behavior_candidates(
    candidates: Iterable[StrategyCandidate],
) -> tuple[StrategyCandidate, ...]:
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


def _component_token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _hand_bond_id(value: object) -> str | None:
    raw = getattr(value, "value", value)
    token = "_".join(
        part
        for part in "".join(
            ch.lower() if ch.isalnum() else " " for ch in str(raw or "")
        ).split()
        if part
    )
    token = token.replace("_of_a_kind", "_kind")
    return token if token in _HAND_BONDS else None


def _observed_hand_strategy_candidates(
    state: Any,
    developments: Iterable[BondDevelopment],
) -> tuple[StrategyCandidate, ...]:
    """Create a generic fallback strategy from repeated public hand use.

    This evidence is intentionally weaker than a mechanistic Bond/behavior engine.
    The composer only consults it when no existing candidate is already pinned, so
    Pair/Two Pair/etc. can become a real strategy without overriding a face-card,
    retrigger, economy, or other concrete engine that merely uses that hand shape.
    """
    counts: dict[str, int] = {}
    for hand, value in (getattr(state, "hand_play_counts", {}) or {}).items():
        bond_id = _hand_bond_id(hand)
        if bond_id is None:
            continue
        try:
            plays = max(0, int(value or 0))
        except (TypeError, ValueError):
            continue
        if plays > 0:
            counts[bond_id] = counts.get(bond_id, 0) + plays
    total = sum(counts.values())
    if total <= 0:
        return ()

    ranked_counts = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    bond_id, plays = ranked_counts[0]
    runner_up = ranked_counts[1][1] if len(ranked_counts) > 1 else 0
    concentration = plays / total
    if plays < 4 or concentration < 0.45:
        return ()

    available = {dev.bond_id for dev in developments}
    if bond_id not in available:
        return ()

    repetition = min(1.0, plays / 12.0)
    confidence = min(0.86, 0.30 + 0.40 * concentration + 0.20 * repetition)
    sustained_dominance = (
        plays >= 10
        and concentration >= 0.42
        and plays >= runner_up + 3
    )
    commitment = (
        StrategyCommitment.PINNED
        if (plays >= 8 and concentration >= 0.50) or sustained_dominance
        else StrategyCommitment.FORMING
    )
    return (
        StrategyCandidate(
            strategy_id=f"observed_hand:{bond_id}",
            bond_ids=(bond_id,),
            sources=(f"observed_hand:{bond_id}",),
            roles=(),
            links=(),
            motif_ids=(),
            commitment=commitment,
            confidence=confidence,
            strength=2.0 + 0.25 * plays + 4.0 * confidence,
            prescriptions=(f"seek_bond:{bond_id}",),
        ),
    )


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


def _single_core_candidate(motif: MotifEvaluation) -> StrategyCandidate:
    present = tuple(dict.fromkeys(str(value) for value in motif.present_components))
    total = len(present) + len(tuple(motif.missing_components or ()))
    completion = 0.0 if total <= 0 else len(present) / total
    confidence = min(0.57, 0.25 + 0.45 * completion)
    return StrategyCandidate(
        strategy_id=str(motif.motif_id),
        bond_ids=tuple(sorted(set(motif.relevant_bonds))),
        sources=present,
        roles=(),
        links=(),
        motif_ids=(str(motif.motif_id),),
        commitment=StrategyCommitment.FORMING,
        confidence=confidence,
        strength=2.0 + 4.0 * confidence + len(present),
        prescriptions=tuple(motif.prescriptions or ()),
    )


def _augment_single_core_candidates(
    candidates: Iterable[StrategyCandidate],
    motifs: Iterable[MotifEvaluation],
) -> tuple[StrategyCandidate, ...]:
    result = list(candidates)
    covered = {
        str(motif_id)
        for candidate in result
        for motif_id in tuple(candidate.motif_ids or ())
    }
    for motif in motifs:
        if (
            motif.state == MotifState.POTENTIAL
            and len(tuple(motif.present_components or ())) == 1
            and str(motif.motif_id) not in covered
            and _single_core_motif(motif) is not None
        ):
            result.append(_single_core_candidate(motif))
    return tuple(
        sorted(
            result,
            key=lambda candidate: (
                int(candidate.commitment),
                candidate.confidence,
                candidate.strength,
                bool(candidate.motif_ids),
                candidate.strategy_id,
            ),
            reverse=True,
        )
    )


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

    raw_motifs = tuple(evaluate_motifs(state, all_developments))
    motifs_list: list[MotifEvaluation] = []
    for motif in raw_motifs:
        promoted = _single_core_motif(motif)
        if motif.state != MotifState.ABSENT:
            motifs_list.append(motif)
        elif promoted is not None:
            motifs_list.append(promoted)
    motifs = tuple(motifs_list)

    role_candidates = _augment_single_core_candidates(
        form_strategy_candidates(all_developments, motifs),
        motifs,
    )
    try:
        behavior_candidates = _sanitize_behavior_candidates(
            form_behavior_strategy_candidates(state, all_developments, motifs)
        )
    except (AttributeError, TypeError, ValueError):
        behavior_candidates = ()
    candidates = merge_strategy_candidates(role_candidates, behavior_candidates)
    if pinned_strategy(candidates) is None:
        candidates = merge_strategy_candidates(
            candidates,
            _observed_hand_strategy_candidates(state, all_developments),
        )
    pinned = pinned_strategy(candidates)
    planned = pinned
    if planned is None:
        planned = next(
            (
                candidate
                for candidate in candidates
                if candidate.commitment == StrategyCommitment.FORMING
            ),
            None,
        )
    plan = build_strategy_plan(planned, all_developments, motifs)

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
