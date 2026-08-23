from __future__ import annotations

"""Mechanical strategy formation above raw Bond ranks.

A Bond rank measures development.  It must not be the prerequisite for noticing
that several mechanics form a coherent engine.  This module therefore reasons over
all positive, mechanically enriched Bond contributions (including R0), builds a
semantic compatibility graph, and turns connected evidence into candidate engines.
Known motifs are accelerators/templates layered on top of the same graph rather
than the only source of strategy knowledge.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization, MechanicalRole
from games.balatro.bonds.motifs import MotifEvaluation, MotifState


class StrategyCommitment(IntEnum):
    EXPLORATORY = 0
    FORMING = 1
    PINNED = 2
    ESTABLISHED = 3
    DOMINANT = 4


@dataclass(frozen=True)
class SemanticLink:
    left_bond: str
    left_source: str
    right_bond: str
    right_source: str
    relation: str


@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    bond_ids: tuple[str, ...]
    sources: tuple[str, ...]
    roles: tuple[MechanicalRole, ...]
    links: tuple[SemanticLink, ...]
    motif_ids: tuple[str, ...]
    commitment: StrategyCommitment
    confidence: float
    strength: float
    prescriptions: tuple[str, ...]

    @property
    def pinned(self) -> bool:
        return self.commitment >= StrategyCommitment.PINNED


# Direction is intentionally irrelevant here.  The graph only needs to know that
# two mechanics have a structural reason to be considered together.  Execution
# policies remain responsible for the direction/timing of the resulting action.
_ROLE_COMPATIBILITY: dict[frozenset[MechanicalRole], str] = {
    frozenset((MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_RANK_PAYOFF)): "RETRIGGER_AMPLIFIES_HELD_PAYOFF",
    frozenset((MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_STATE_PAYOFF)): "RETRIGGER_AMPLIFIES_HELD_PAYOFF",
    frozenset((MechanicalRole.HELD_RETRIGGER, MechanicalRole.HELD_CARD_XMULT)): "RETRIGGER_AMPLIFIES_HELD_XMULT",
    frozenset((MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.RANK_PAYOFF)): "DENSITY_SUPPORTS_RANK_PAYOFF",
    frozenset((MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.HELD_RANK_PAYOFF)): "DENSITY_SUPPORTS_HELD_RANK_PAYOFF",
    frozenset((MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.SUIT_PAYOFF)): "DENSITY_SUPPORTS_SUIT_PAYOFF",
    frozenset((MechanicalRole.DENSITY_INFRASTRUCTURE, MechanicalRole.ENHANCEMENT_PAYOFF)): "DENSITY_SUPPORTS_ENHANCEMENT_PAYOFF",
    frozenset((MechanicalRole.ENHANCEMENT_FEED, MechanicalRole.ENHANCEMENT_PAYOFF)): "FEED_SUPPORTS_ENHANCEMENT_PAYOFF",
    frozenset((MechanicalRole.DECK_THIN_ENGINE, MechanicalRole.DECK_THIN_PAYOFF)): "ENGINE_FEEDS_DECK_THIN_PAYOFF",
    frozenset((MechanicalRole.ECONOMY_ENGINE, MechanicalRole.ECONOMY_PAYOFF)): "ENGINE_FEEDS_ECONOMY_PAYOFF",
    frozenset((MechanicalRole.HAND_LEVEL_ENGINE, MechanicalRole.HAND_PAYOFF)): "LEVEL_ENGINE_SUPPORTS_HAND_PAYOFF",
    frozenset((MechanicalRole.COPY_ENGINE, MechanicalRole.SCALER)): "COPY_AMPLIFIES_SCALER",
    frozenset((MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RETRIGGER)): "COPY_AMPLIFIES_RETRIGGER",
    frozenset((MechanicalRole.COPY_ENGINE, MechanicalRole.HELD_RANK_PAYOFF)): "COPY_AMPLIFIES_HELD_PAYOFF",
    frozenset((MechanicalRole.COPY_ENGINE, MechanicalRole.HAND_PAYOFF)): "COPY_AMPLIFIES_HAND_PAYOFF",
    frozenset((MechanicalRole.COPY_ENGINE, MechanicalRole.ENHANCEMENT_PAYOFF)): "COPY_AMPLIFIES_ENHANCEMENT_PAYOFF",
}


@dataclass(frozen=True)
class _Evidence:
    bond_id: str
    source: str
    value: float
    roles: tuple[MechanicalRole, ...]
    targets: tuple[str, ...]


def _evidence(developments: Iterable[BondDevelopment]) -> tuple[_Evidence, ...]:
    result: list[_Evidence] = []
    for raw in developments:
        dev = enrich_development(raw)
        for contribution in dev.contributions:
            if float(contribution.value) <= 0.0 or not contribution.roles:
                continue
            result.append(
                _Evidence(
                    bond_id=dev.bond_id,
                    source=str(contribution.source),
                    value=float(contribution.value),
                    roles=tuple(contribution.roles),
                    targets=tuple(str(target) for target in contribution.targets),
                )
            )
    return tuple(result)


def _semantic_relation(left: _Evidence, right: _Evidence) -> str | None:
    if left.bond_id == right.bond_id and left.source == right.source:
        return None

    for left_role in left.roles:
        for right_role in right.roles:
            relation = _ROLE_COMPATIBILITY.get(frozenset((left_role, right_role)))
            if relation:
                return relation

    # Matching explicit targets are weaker evidence than a role-level feed/amplify
    # relationship, but still establish a coherent mechanical axis.
    if set(left.targets).intersection(right.targets):
        return "SHARED_MECHANICAL_TARGET"
    return None


def _component_indices(evidence: tuple[_Evidence, ...], links: tuple[SemanticLink, ...]) -> tuple[tuple[int, ...], ...]:
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(evidence))}
    source_to_indices: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(evidence):
        source_to_indices.setdefault((item.bond_id, item.source), []).append(index)

    for link in links:
        lefts = source_to_indices.get((link.left_bond, link.left_source), ())
        rights = source_to_indices.get((link.right_bond, link.right_source), ())
        for left in lefts:
            for right in rights:
                if left == right:
                    continue
                adjacency[left].add(right)
                adjacency[right].add(left)

    seen: set[int] = set()
    components: list[tuple[int, ...]] = []
    for start in range(len(evidence)):
        if start in seen or not adjacency[start]:
            continue
        stack = [start]
        group: set[int] = set()
        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            seen.add(current)
            stack.extend(adjacency[current] - group)
        if len(group) >= 2:
            components.append(tuple(sorted(group)))
    return tuple(components)


def _realization_score(dev: BondDevelopment) -> float:
    return {
        BondRealization.DORMANT: 0.0,
        BondRealization.PARTIAL: 0.25,
        BondRealization.ACTIVE: 0.75,
        BondRealization.MATURE: 1.0,
    }[dev.realization]


def _motif_overlap(motif: MotifEvaluation, bond_ids: set[str]) -> int:
    return len(set(motif.relevant_bonds).intersection(bond_ids))


def _motif_completion(motif: MotifEvaluation) -> float:
    total = len(motif.present_components) + len(motif.missing_components)
    return 0.0 if total <= 0 else len(motif.present_components) / total


def _commitment(
    *,
    source_count: int,
    bond_count: int,
    link_count: int,
    confidence: float,
    motifs: tuple[MotifEvaluation, ...],
    developments: dict[str, BondDevelopment],
) -> StrategyCommitment:
    active_motif = any(motif.state >= MotifState.ACTIVE for motif in motifs)
    mature_motif = any(motif.state >= MotifState.MATURE for motif in motifs)
    potential_half = any(
        motif.state == MotifState.POTENTIAL
        and len(motif.present_components) >= 2
        and _motif_completion(motif) >= 0.5
        for motif in motifs
    )
    realized = sum(
        1
        for dev in developments.values()
        if dev.realization >= BondRealization.ACTIVE and dev.rank >= BondRank.R1
    )

    if mature_motif or (confidence >= 0.90 and source_count >= 5 and realized >= 3):
        return StrategyCommitment.DOMINANT
    if active_motif or (confidence >= 0.78 and source_count >= 4 and realized >= 2):
        return StrategyCommitment.ESTABLISHED
    # Crucial architecture rule: a coherent half-complete known package or a strong
    # mechanically linked pair can be pinned before its Bonds are highly ranked.
    if potential_half or (confidence >= 0.58 and source_count >= 2 and link_count >= 1):
        return StrategyCommitment.PINNED
    if source_count >= 2 and link_count >= 1:
        return StrategyCommitment.FORMING
    return StrategyCommitment.EXPLORATORY


def form_strategy_candidates(
    developments: Iterable[BondDevelopment],
    motifs: Iterable[MotifEvaluation] = (),
) -> tuple[StrategyCandidate, ...]:
    dev_tuple = tuple(developments)
    dev_map = {dev.bond_id: dev for dev in dev_tuple}
    evidence = _evidence(dev_tuple)

    links: list[SemanticLink] = []
    for index, left in enumerate(evidence):
        for right in evidence[index + 1 :]:
            relation = _semantic_relation(left, right)
            if relation is None:
                continue
            links.append(
                SemanticLink(
                    left_bond=left.bond_id,
                    left_source=left.source,
                    right_bond=right.bond_id,
                    right_source=right.source,
                    relation=relation,
                )
            )
    link_tuple = tuple(links)
    components = _component_indices(evidence, link_tuple)

    candidates: list[StrategyCandidate] = []
    all_motifs = tuple(motifs)
    for ordinal, indices in enumerate(components, start=1):
        group = tuple(evidence[index] for index in indices)
        bond_ids = tuple(sorted({item.bond_id for item in group}))
        bond_set = set(bond_ids)
        sources = tuple(dict.fromkeys(item.source for item in group))
        roles = tuple(sorted({role for item in group for role in item.roles}, key=str))
        component_links = tuple(
            link
            for link in link_tuple
            if link.left_bond in bond_set and link.right_bond in bond_set
        )
        relevant_motifs = tuple(
            motif
            for motif in all_motifs
            if motif.state != MotifState.ABSENT and _motif_overlap(motif, bond_set) >= 2
        )

        evidence_value = sum(min(8.0, item.value) for item in group)
        density = min(1.0, len(component_links) / max(1.0, len(group) - 1.0))
        source_factor = min(1.0, len(sources) / 4.0)
        evidence_factor = min(1.0, evidence_value / 20.0)
        motif_factor = max((_motif_completion(motif) for motif in relevant_motifs), default=0.0)
        confidence = min(
            1.0,
            0.15 + 0.30 * density + 0.25 * source_factor + 0.20 * evidence_factor + 0.25 * motif_factor,
        )
        related_devs = {bond_id: dev_map[bond_id] for bond_id in bond_ids if bond_id in dev_map}
        commitment = _commitment(
            source_count=len(sources),
            bond_count=len(bond_ids),
            link_count=len(component_links),
            confidence=confidence,
            motifs=relevant_motifs,
            developments=related_devs,
        )
        prescriptions = tuple(
            dict.fromkeys(
                prescription
                for motif in relevant_motifs
                for prescription in motif.prescriptions
            )
        )
        motif_ids = tuple(motif.motif_id for motif in relevant_motifs)
        strategy_id = motif_ids[0] if motif_ids else "semantic:" + "+".join(bond_ids or (f"engine{ordinal}",))
        rank_strength = sum(max(0, int(dev.rank)) for dev in related_devs.values())
        realization_strength = sum(_realization_score(dev) for dev in related_devs.values())
        strength = evidence_value + 2.0 * len(component_links) + 4.0 * confidence + rank_strength + realization_strength

        candidates.append(
            StrategyCandidate(
                strategy_id=strategy_id,
                bond_ids=bond_ids,
                sources=sources,
                roles=roles,
                links=component_links,
                motif_ids=motif_ids,
                commitment=commitment,
                confidence=confidence,
                strength=strength,
                prescriptions=prescriptions,
            )
        )

    # A known motif can be strategically meaningful even when its components do not
    # yet form a generic role-connected component (for example a converter/feed
    # package whose role registry is still sparse).  Preserve that signal as a
    # template candidate instead of making motif coverage a prerequisite for graph
    # connectivity.
    covered_motifs = {motif_id for candidate in candidates for motif_id in candidate.motif_ids}
    for motif in all_motifs:
        if motif.state == MotifState.ABSENT or motif.motif_id in covered_motifs:
            continue
        if len(motif.present_components) < 2:
            continue
        bond_ids = tuple(sorted(set(motif.relevant_bonds)))
        completion = _motif_completion(motif)
        confidence = min(1.0, 0.35 + 0.55 * completion)
        commitment = (
            StrategyCommitment.ESTABLISHED
            if motif.state >= MotifState.ACTIVE
            else StrategyCommitment.PINNED
            if completion >= 0.5
            else StrategyCommitment.FORMING
        )
        candidates.append(
            StrategyCandidate(
                strategy_id=motif.motif_id,
                bond_ids=bond_ids,
                sources=tuple(motif.present_components),
                roles=(),
                links=(),
                motif_ids=(motif.motif_id,),
                commitment=commitment,
                confidence=confidence,
                strength=5.0 * confidence + len(motif.present_components),
                prescriptions=motif.prescriptions,
            )
        )

    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                int(candidate.commitment),
                candidate.confidence,
                candidate.strength,
                candidate.strategy_id,
            ),
            reverse=True,
        )
    )


def pinned_strategy(candidates: Iterable[StrategyCandidate]) -> StrategyCandidate | None:
    return next((candidate for candidate in candidates if candidate.pinned), None)
