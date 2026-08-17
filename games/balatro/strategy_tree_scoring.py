from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .strategy_topology import StrategyTopology


@dataclass(frozen=True)
class StrategyTreeNodeScore:
    """One topology node's evidence decomposition.

    ``foundation_score`` is diagnostic branch evidence and may include discounted
    positive descendant evidence. ``effective_score`` is actionable only for
    leaves and never reuses descendant evidence that already propagated upward.
    """

    strategy_id: str
    direct_evidence: float
    foundation_score: float
    effective_score: float
    active: bool
    is_leaf: bool
    is_fallback_leaf: bool
    rationale: tuple[str, ...] = ()


class StrategyTreeEvidenceScorer:
    """Apply tree semantics to already-computed direct strategy evidence.

    This class owns topology propagation only. Joker tier weights, economy,
    survival, cartridge effectiveness and candidate purchase value remain outside
    it so the tree does not become a second scoring system.
    """

    def __init__(
        self,
        topology: StrategyTopology,
        *,
        upward_decay: float = 0.50,
        ancestor_inheritance_decay: float = 1.0,
        specific_activation_floor: float = 1.0,
    ) -> None:
        if not 0.0 <= float(upward_decay) <= 1.0:
            raise ValueError("upward_decay must be within [0, 1]")
        if not 0.0 <= float(ancestor_inheritance_decay) <= 1.0:
            raise ValueError("ancestor_inheritance_decay must be within [0, 1]")
        if float(specific_activation_floor) < 0.0:
            raise ValueError("specific_activation_floor must be non-negative")
        self.topology = topology
        self.upward_decay = float(upward_decay)
        self.ancestor_inheritance_decay = float(ancestor_inheritance_decay)
        self.specific_activation_floor = float(specific_activation_floor)

    def _branch_has_qualifying_direct(
        self,
        strategy_id: str,
        direct: Mapping[str, float],
    ) -> bool:
        if direct[strategy_id] >= self.specific_activation_floor:
            return True
        return any(
            self._branch_has_qualifying_direct(child_id, direct)
            for child_id in self.topology.children_by_id[strategy_id]
        )

    def score(
        self,
        direct_evidence: Mapping[str, float],
    ) -> Mapping[str, StrategyTreeNodeScore]:
        unknown = set(direct_evidence) - set(self.topology.nodes)
        if unknown:
            joined = ", ".join(sorted(unknown))
            raise KeyError(f"direct evidence references unknown strategy nodes: {joined}")

        direct = {
            strategy_id: float(direct_evidence.get(strategy_id, 0.0))
            for strategy_id in self.topology.nodes
        }
        foundation = {
            strategy_id: direct[strategy_id]
            for strategy_id in self.topology.nodes
        }
        notes: dict[str, list[str]] = {
            strategy_id: [] for strategy_id in self.topology.nodes
        }

        # Descendant evidence proves broader foundations. Only positive evidence
        # propagates upward; a conflict with one specialized child must not make
        # the broader parent itself look mechanically contradictory.
        for descendant_id, descendant_direct in direct.items():
            if descendant_direct <= 0.0:
                continue
            for distance, ancestor_id in enumerate(
                self.topology.ancestors(descendant_id),
                start=1,
            ):
                propagated = descendant_direct * (self.upward_decay ** distance)
                foundation[ancestor_id] += propagated
                notes[ancestor_id].append(
                    f"+{propagated:.3f} foundation from descendant "
                    f"{descendant_id} at distance {distance}"
                )

        scores: dict[str, StrategyTreeNodeScore] = {}
        for strategy_id, node in self.topology.nodes.items():
            is_leaf = self.topology.is_leaf(strategy_id)
            if not is_leaf:
                scores[strategy_id] = StrategyTreeNodeScore(
                    strategy_id=strategy_id,
                    direct_evidence=direct[strategy_id],
                    foundation_score=foundation[strategy_id],
                    effective_score=0.0,
                    active=False,
                    is_leaf=False,
                    is_fallback_leaf=False,
                    rationale=tuple(notes[strategy_id]),
                )
                continue

            parent_id = self.topology.parent_by_id[strategy_id]
            sibling_specific_active = False
            if node.is_fallback_leaf and parent_id is not None:
                sibling_specific_active = any(
                    sibling_id != strategy_id
                    and not self.topology.nodes[sibling_id].is_fallback_leaf
                    and self._branch_has_qualifying_direct(sibling_id, direct)
                    for sibling_id in self.topology.children_by_id[parent_id]
                )

            own_specific_evidence = (
                direct[strategy_id] >= self.specific_activation_floor
            )
            inherited_ancestor_direct = 0.0
            if own_specific_evidence or node.is_fallback_leaf:
                for distance, ancestor_id in enumerate(
                    self.topology.ancestors(strategy_id),
                    start=1,
                ):
                    inherited_ancestor_direct += direct[ancestor_id] * (
                        self.ancestor_inheritance_decay ** distance
                    )

            if node.is_fallback_leaf:
                active = not sibling_specific_active and (
                    direct[strategy_id] > 0.0 or inherited_ancestor_direct > 0.0
                )
                if sibling_specific_active:
                    notes[strategy_id].append(
                        "fallback suppressed by qualifying child-specific sibling evidence"
                    )
            else:
                # Broad parent evidence alone never activates a specific child.
                active = own_specific_evidence
                if inherited_ancestor_direct and not own_specific_evidence:
                    notes[strategy_id].append(
                        "ancestor foundation present but qualifying child-specific evidence absent"
                    )

            effective = (
                direct[strategy_id] + inherited_ancestor_direct if active else 0.0
            )
            if active and inherited_ancestor_direct:
                notes[strategy_id].append(
                    f"{inherited_ancestor_direct:+.3f} inherited native ancestor evidence"
                )

            scores[strategy_id] = StrategyTreeNodeScore(
                strategy_id=strategy_id,
                direct_evidence=direct[strategy_id],
                foundation_score=foundation[strategy_id],
                effective_score=effective,
                active=active,
                is_leaf=True,
                is_fallback_leaf=node.is_fallback_leaf,
                rationale=tuple(notes[strategy_id]),
            )

        return MappingProxyType(scores)

    def rank_leaves(
        self,
        direct_evidence: Mapping[str, float],
    ) -> tuple[StrategyTreeNodeScore, ...]:
        scores = self.score(direct_evidence)
        return tuple(
            sorted(
                (
                    score
                    for score in scores.values()
                    if score.is_leaf and score.active and score.effective_score > 0.0
                ),
                key=lambda score: (-score.effective_score, score.strategy_id),
            )
        )
