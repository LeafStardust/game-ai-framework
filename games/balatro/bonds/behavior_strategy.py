from __future__ import annotations

"""Behavior-backed strategy inference for the Bond composition machine.

The build profiler already discovers Joker outputs, requirements, scaling inputs and
amplifiers from the real Joker implementations. This module converts that generic
vocabulary into strategy candidates so the Bond system does not require a hand-made
pair table for every useful Balatro interaction.
"""

from dataclasses import dataclass
from typing import Iterable

from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_semantics import SemanticLink, StrategyCandidate, StrategyCommitment
from games.balatro.build.profile import BalatroBuildProfiler


def _token(value: object) -> str:
    raw = str(value or "").lower()
    token = "".join(ch for ch in raw if ch.isalnum())
    return token[:-5] if token.endswith("joker") else token


def _source_bonds(developments: tuple[BondDevelopment, ...]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for dev in developments:
        for contribution in dev.contributions:
            token = _token(contribution.source)
            if token:
                mapping.setdefault(token, set()).add(dev.bond_id)
    return mapping


def _descriptor_bonds(source: str, mapping: dict[str, set[str]]) -> tuple[str, ...]:
    token = _token(source)
    matches: set[str] = set(mapping.get(token, ()))
    if not matches:
        for candidate, bond_ids in mapping.items():
            if candidate and (candidate in token or token in candidate):
                matches.update(bond_ids)
    return tuple(sorted(matches))


def _feature_bonds(feature: str) -> tuple[str, ...]:
    lower = str(feature).lower()
    rank = lower.split(":")[-1].upper()
    if "rank:" in lower:
        return {
            "K": ("kings", "held_cards"),
            "Q": ("queens", "held_cards"),
            "J": ("jacks", "face_cards"),
            "A": ("aces",),
        }.get(rank, ("low_ranks",) if rank in {"2", "3", "4", "5"} else ())
    if "enhancement:steel" in lower or lower == "held:effect":
        return ("steel", "held_cards")
    if "enhancement:glass" in lower:
        return ("glass", "enhanced_cards")
    if "enhancement:gold" in lower:
        return ("gold_economy", "enhanced_cards")
    if lower.startswith("suit:") or lower.startswith("held:suit:"):
        suit = lower.split(":")[-1]
        return (suit,) if suit in {"hearts", "spades", "clubs", "diamonds"} else ()
    if lower.startswith("hand:"):
        hand = lower.split(":", 1)[1].lower()
        aliases = {
            "high_card": "high_card", "pair": "pair", "two_pair": "two_pair",
            "three_of_a_kind": "three_kind", "four_of_a_kind": "four_kind",
            "straight": "straight", "flush": "flush", "full_house": "full_house",
            "straight_flush": "straight_flush", "five_of_a_kind": "five_kind",
            "flush_house": "flush_house", "flush_five": "flush_five",
        }
        return (aliases[hand],) if hand in aliases else ()
    if lower == "economy":
        return ("cash", "gold_economy")
    if lower == "held:retrigger":
        return ("held_retrigger",)
    if lower == "played:retrigger":
        return ("played_retrigger",)
    return ()


@dataclass(frozen=True)
class _Node:
    source: str
    bond_ids: tuple[str, ...]
    outputs: frozenset[str]
    requires: frozenset[str]
    scales_with: frozenset[str]
    amplifies: frozenset[str]
    value: float


def _nodes(state, developments: tuple[BondDevelopment, ...]):
    profile = BalatroBuildProfiler().profile(state)
    mapping = _source_bonds(developments)
    nodes: list[_Node] = []
    for descriptor in profile.descriptors(kind="JOKER"):
        bond_ids = _descriptor_bonds(descriptor.source, mapping)
        if not bond_ids:
            continue
        outputs = frozenset(set(descriptor.produces) | set(descriptor.transforms))
        nodes.append(
            _Node(
                source=str(descriptor.source),
                bond_ids=bond_ids,
                outputs=outputs,
                requires=frozenset(descriptor.requires),
                scales_with=frozenset(descriptor.scales_with),
                amplifies=frozenset(descriptor.amplifies),
                value=4.0 + len(outputs) + 0.5 * len(descriptor.requires) + 0.25 * len(descriptor.scales_with),
            )
        )
    for feature, strength in profile.feature_strengths:
        if float(strength) <= 0.0:
            continue
        bond_ids = _feature_bonds(feature)
        if not bond_ids:
            continue
        nodes.append(
            _Node(
                source=f"feature:{feature}",
                bond_ids=bond_ids,
                outputs=frozenset({str(feature)}),
                requires=frozenset(),
                scales_with=frozenset(),
                amplifies=frozenset(),
                value=min(6.0, 1.0 + float(strength) ** 0.5),
            )
        )
    return profile, tuple(nodes)


def _relation(left: _Node, right: _Node) -> str | None:
    if left.outputs.intersection(right.requires) or right.outputs.intersection(left.requires):
        return "OUTPUT_SATISFIES_REQUIREMENT"
    if left.outputs.intersection(right.scales_with) or right.outputs.intersection(left.scales_with):
        return "OUTPUT_FEEDS_SCALING"
    if left.amplifies.intersection(right.outputs) or right.amplifies.intersection(left.outputs):
        return "AMPLIFIER_TARGETS_OUTPUT"
    return None


def _graph(nodes: tuple[_Node, ...]):
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(nodes))}
    links: list[tuple[int, int, str]] = []
    for index, left in enumerate(nodes):
        for j in range(index + 1, len(nodes)):
            relation = _relation(left, nodes[j])
            if relation is None:
                continue
            adjacency[index].add(j)
            adjacency[j].add(index)
            links.append((index, j, relation))
    return adjacency, tuple(links)


def _components(adjacency: dict[int, set[int]]) -> tuple[tuple[int, ...], ...]:
    seen: set[int] = set()
    groups: list[tuple[int, ...]] = []
    for start, neighbors in adjacency.items():
        if start in seen or not neighbors:
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
            groups.append(tuple(sorted(group)))
    return tuple(groups)


def _motif_completion(motif: MotifEvaluation) -> float:
    total = len(motif.present_components) + len(motif.missing_components)
    return 0.0 if total <= 0 else len(motif.present_components) / total


def _feature_goals(group: tuple[_Node, ...], available: set[str]) -> tuple[str, ...]:
    desired: set[str] = set()
    for node in group:
        desired.update(node.requires - available)
        desired.update(node.scales_with - available)
        desired.update(node.amplifies - available)
    return tuple(sorted(feature for feature in desired if feature))


def form_behavior_strategy_candidates(state, developments: Iterable[BondDevelopment], motifs: Iterable[MotifEvaluation] = ()) -> tuple[StrategyCandidate, ...]:
    devs = tuple(developments)
    profile, nodes = _nodes(state, devs)
    adjacency, raw_links = _graph(nodes)
    all_motifs = tuple(motifs)
    available = {feature for feature, strength in profile.feature_strengths if float(strength) > 0.0}
    for node in nodes:
        available.update(node.outputs)
    candidates: list[StrategyCandidate] = []

    for ordinal, indices in enumerate(_components(adjacency), start=1):
        group = tuple(nodes[index] for index in indices)
        bond_ids = tuple(sorted({bond for node in group for bond in node.bond_ids}))
        bond_set = set(bond_ids)
        component_links = tuple(
            SemanticLink(
                left_bond=next(iter(nodes[left].bond_ids), "behavior"),
                left_source=nodes[left].source,
                right_bond=next(iter(nodes[right].bond_ids), "behavior"),
                right_source=nodes[right].source,
                relation=relation,
            )
            for left, right, relation in raw_links
            if left in indices and right in indices
        )
        relevant_motifs = tuple(
            motif for motif in all_motifs
            if motif.state != MotifState.ABSENT and len(set(motif.relevant_bonds).intersection(bond_set)) >= 2
        )
        motif_factor = max((_motif_completion(motif) for motif in relevant_motifs), default=0.0)
        link_density = min(1.0, len(component_links) / max(1, len(group) - 1))
        confidence = min(1.0, 0.20 + 0.35 * link_density + 0.20 * min(1.0, len(group) / 4.0) + 0.25 * motif_factor)
        active = any(motif.state >= MotifState.ACTIVE for motif in relevant_motifs)
        half = any(_motif_completion(motif) >= 0.5 for motif in relevant_motifs)
        commitment = (
            StrategyCommitment.ESTABLISHED if active
            else StrategyCommitment.PINNED if half or (confidence >= 0.62 and len(group) >= 2)
            else StrategyCommitment.FORMING
        )
        motif_ids = tuple(motif.motif_id for motif in relevant_motifs)
        strategy_id = motif_ids[0] if motif_ids else "behavior:" + "+".join(bond_ids or (f"engine{ordinal}",))
        goals = _feature_goals(group, available)
        prescriptions = tuple(dict.fromkeys(
            [p for motif in relevant_motifs for p in motif.prescriptions]
            + [f"seek_feature:{feature}" for feature in goals]
        ))
        candidates.append(
            StrategyCandidate(
                strategy_id=strategy_id,
                bond_ids=bond_ids,
                sources=tuple(node.source for node in group),
                roles=(),
                links=component_links,
                motif_ids=motif_ids,
                commitment=commitment,
                confidence=confidence,
                strength=sum(node.value for node in group) + 2.5 * len(component_links) + 4.0 * confidence,
                prescriptions=prescriptions,
            )
        )
    return tuple(candidates)


def merge_strategy_candidates(*families: Iterable[StrategyCandidate]) -> tuple[StrategyCandidate, ...]:
    """Merge duplicate strategy identities without discarding evidence channels."""
    by_id: dict[str, StrategyCandidate] = {}
    for candidate in (item for family in families for item in family):
        current = by_id.get(candidate.strategy_id)
        if current is None:
            by_id[candidate.strategy_id] = candidate
            continue
        winner = max((current, candidate), key=lambda value: (int(value.commitment), value.confidence, value.strength))
        by_id[candidate.strategy_id] = StrategyCandidate(
            strategy_id=winner.strategy_id,
            bond_ids=tuple(sorted(set(current.bond_ids) | set(candidate.bond_ids))),
            sources=tuple(dict.fromkeys((*current.sources, *candidate.sources))),
            roles=tuple(sorted(set(current.roles) | set(candidate.roles), key=str)),
            links=tuple(dict.fromkeys((*current.links, *candidate.links))),
            motif_ids=tuple(dict.fromkeys((*current.motif_ids, *candidate.motif_ids))),
            commitment=max(current.commitment, candidate.commitment),
            confidence=max(current.confidence, candidate.confidence),
            strength=max(current.strength, candidate.strength) + 0.25 * min(current.strength, candidate.strength),
            prescriptions=tuple(dict.fromkeys((*current.prescriptions, *candidate.prescriptions))),
        )
    return tuple(sorted(by_id.values(), key=lambda value: (int(value.commitment), value.confidence, value.strength, value.strategy_id), reverse=True))
