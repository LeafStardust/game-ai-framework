from __future__ import annotations

"""Applied strategy plan above semantic strategy discovery.

The semantic graph answers "what coherent engine is present?". This layer answers
"what are we building next?". FORMING strategies receive bounded construction
and acquisition authority; PINNED and stronger strategies additionally receive
preservation/execution prescriptions.
"""

from dataclasses import dataclass
from typing import Iterable

from games.balatro.bonds.model import BondDevelopment, BondRank
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_semantics import StrategyCandidate, StrategyCommitment


@dataclass(frozen=True)
class StrategyBondGoal:
    bond_id: str
    rank: BondRank
    next_rank: BondRank | None
    contribution: float
    next_rank_threshold: float | None
    points_to_next_rank: float | None
    priority: float


@dataclass(frozen=True)
class StrategyPlan:
    strategy_id: str
    commitment: StrategyCommitment
    confidence: float
    strength: float
    core_sources: tuple[str, ...]
    bond_goals: tuple[StrategyBondGoal, ...]
    missing_features: tuple[str, ...]
    present_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    prescriptions: tuple[str, ...]
    completion: float

    @property
    def next_priority(self) -> StrategyBondGoal | None:
        return self.bond_goals[0] if self.bond_goals else None


def _next_rank(rank: BondRank) -> BondRank | None:
    if rank < BondRank.R0:
        return BondRank.R1
    if rank >= BondRank.R5:
        return None
    return BondRank(int(rank) + 1)


def _feature_goals(candidate: StrategyCandidate) -> tuple[str, ...]:
    values: list[str] = []
    for prescription in candidate.prescriptions:
        text = str(prescription)
        if text.startswith("seek_feature:"):
            feature = text.split(":", 1)[1].strip()
            if feature:
                values.append(feature)
    return tuple(dict.fromkeys(values))


def _motif_components(
    candidate: StrategyCandidate,
    motifs: Iterable[MotifEvaluation],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    relevant = [
        motif
        for motif in motifs
        if motif.motif_id in set(candidate.motif_ids)
        and motif.state != MotifState.ABSENT
    ]
    present = tuple(
        dict.fromkeys(
            component for motif in relevant for component in motif.present_components
        )
    )
    missing = tuple(
        dict.fromkeys(
            component for motif in relevant for component in motif.missing_components
        )
    )
    return present, missing


def _participating_bonds(candidate: StrategyCandidate) -> set[str]:
    linked: set[str] = set()
    for link in candidate.links:
        linked.add(link.left_bond)
        linked.add(link.right_bond)
    return linked or set(candidate.bond_ids)


def _goal_priority(
    dev: BondDevelopment,
    *,
    linked: bool,
    commitment: StrategyCommitment,
) -> float:
    if dev.rank >= BondRank.R5:
        return -1.0
    gap = dev.points_to_next_rank
    threshold = dev.next_rank_threshold
    closeness = 0.0
    if gap is not None and threshold and threshold > 0:
        closeness = max(0.0, min(1.0, 1.0 - float(gap) / float(threshold)))
    return (
        4.0 * (1.0 if linked else 0.0)
        + 0.75 * int(max(BondRank.R0, dev.rank))
        + 2.0 * closeness
        + 0.25 * int(commitment)
    )


def _completion_fraction(
    *,
    bond_fraction: float,
    present_components: tuple[str, ...],
    missing_components: tuple[str, ...],
) -> float:
    """Measure plan construction without making named motifs mandatory.

    Known motifs add useful concrete package-completion evidence, so motif-bearing
    strategies blend Bond development with component completion. Generic semantic
    strategies have no motif component denominator; their completion must therefore
    be determined by their participating Bond development alone rather than being
    permanently capped at 55%.
    """
    component_total = len(present_components) + len(missing_components)
    if component_total <= 0:
        return max(0.0, min(1.0, bond_fraction))
    component_fraction = len(present_components) / component_total
    return max(0.0, min(1.0, 0.55 * bond_fraction + 0.45 * component_fraction))


def build_strategy_plan(
    candidate: StrategyCandidate | None,
    developments: Iterable[BondDevelopment],
    motifs: Iterable[MotifEvaluation] = (),
) -> StrategyPlan | None:
    if candidate is None or candidate.commitment < StrategyCommitment.FORMING:
        return None

    dev_map = {dev.bond_id: dev for dev in developments}
    participating = _participating_bonds(candidate)
    goals: list[StrategyBondGoal] = []
    for bond_id in candidate.bond_ids:
        dev = dev_map.get(bond_id)
        if dev is None or dev.rank >= BondRank.R5:
            continue
        goals.append(
            StrategyBondGoal(
                bond_id=bond_id,
                rank=dev.rank,
                next_rank=_next_rank(dev.rank),
                contribution=float(dev.contribution),
                next_rank_threshold=dev.next_rank_threshold,
                points_to_next_rank=dev.points_to_next_rank,
                priority=_goal_priority(
                    dev,
                    linked=bond_id in participating,
                    commitment=candidate.commitment,
                ),
            )
        )
    goals.sort(
        key=lambda goal: (
            goal.priority,
            -float(goal.points_to_next_rank or 0.0),
            goal.bond_id,
        ),
        reverse=True,
    )

    present, missing = _motif_components(candidate, motifs)
    feature_goals = _feature_goals(candidate)

    completed_bonds = sum(
        1
        for bond_id in candidate.bond_ids
        if dev_map.get(bond_id) and dev_map[bond_id].rank >= BondRank.R2
    )
    bond_fraction = completed_bonds / max(1, len(candidate.bond_ids))
    completion = _completion_fraction(
        bond_fraction=bond_fraction,
        present_components=present,
        missing_components=missing,
    )

    # FORMING is deliberately construction-only. It may tell acquisition layers
    # what missing feature/component/Bond to seek, but it may not yet protect
    # pieces, resist replacements, or dictate hand execution. Those stronger
    # prescriptions become authoritative only once the strategy is PINNED.
    plan_prescriptions: list[str] = []
    if candidate.commitment >= StrategyCommitment.PINNED:
        plan_prescriptions.extend(candidate.prescriptions)
    else:
        plan_prescriptions.extend(f"seek_feature:{feature}" for feature in feature_goals)
    for goal in goals:
        if goal.next_rank is not None:
            plan_prescriptions.append(f"seek_bond:{goal.bond_id}:{goal.next_rank.name}")
    for component in missing:
        plan_prescriptions.append(f"seek_component:{component}")

    return StrategyPlan(
        strategy_id=candidate.strategy_id,
        commitment=candidate.commitment,
        confidence=float(candidate.confidence),
        strength=float(candidate.strength),
        core_sources=tuple(candidate.sources),
        bond_goals=tuple(goals),
        missing_features=feature_goals,
        present_components=present,
        missing_components=missing,
        prescriptions=tuple(dict.fromkeys(plan_prescriptions)),
        completion=completion,
    )
