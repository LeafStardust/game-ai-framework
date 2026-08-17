from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Mapping

from games.balatro.strategy import (
    AVAILABLE,
    BANNED,
    BRONZE,
    CANDIDATE,
    COMMITTED,
    GOLD,
    HIGHLIGHTED,
    MATURE,
    NEUTRAL,
    SILVER,
    StrategicItemEvaluation,
)
from games.balatro.strategy_conditional_relationships import (
    StateAwareBalatroStrategyTracker,
)
from games.balatro.strategy_topology import StrategyTopology
from games.balatro.strategy_tree_scoring import (
    StrategyTreeEvidenceScorer,
    StrategyTreeNodeScore,
)


_RELATIONSHIP_PRIORITY = {
    NEUTRAL: 0,
    BRONZE: 1,
    SILVER: 2,
    GOLD: 3,
    BANNED: 4,
}
_POSITIVE_RELATIONSHIP_PRIORITY = {
    NEUTRAL: 0,
    BANNED: 0,
    BRONZE: 1,
    SILVER: 2,
    GOLD: 3,
}


class TreeAwareStateAwareBalatroStrategyTracker(StateAwareBalatroStrategyTracker):
    """Production strategy tracker during the flat -> tree catalogue migration.

    Existing ``StrategyAssessment.score`` remains the compatibility surface for all
    already-green D1-D14 consumers. Internally, node direct evidence is separated
    from ancestor foundation and only the current branch frontier is exposed to
    the actionable ranking.
    """

    def __init__(
        self,
        definitions,
        *,
        topology: StrategyTopology,
        modifier_provider=None,
    ) -> None:
        super().__init__(definitions, modifier_provider=modifier_provider)
        missing_definitions = set(topology.nodes) - set(self.definitions)
        missing_nodes = set(self.definitions) - set(topology.nodes)
        if missing_definitions or missing_nodes:
            raise ValueError(
                "strategy definitions/topology ids must match exactly; "
                f"missing_definitions={sorted(missing_definitions)}; "
                f"missing_nodes={sorted(missing_nodes)}"
            )
        self.topology = topology
        self.tree_scorer = StrategyTreeEvidenceScorer(topology)
        self._last_direct_evidence: Mapping[str, float] = MappingProxyType({})
        self._last_tree_node_scores: Mapping[str, StrategyTreeNodeScore] = (
            MappingProxyType({})
        )
        self._last_direct_assessments = MappingProxyType({})

    def _tree_modifier(self, config, strategy_id: str):
        modifier = self._modifier(config, strategy_id)
        if modifier:
            return modifier
        for ancestor_id in self.topology.ancestors(strategy_id):
            modifier = self._modifier(config, ancestor_id)
            if modifier:
                return modifier
        return {}

    def effectiveness(self, state, strategy_id: str) -> float:
        config = self._config(state)
        modifier = self._tree_modifier(config, strategy_id)
        if modifier.get("enabled", True) is False:
            return 0.0
        try:
            return max(0.0, float(modifier.get("effectiveness", 1.0)))
        except (TypeError, ValueError):
            return 1.0

    def base_strategy_score(self, state, strategy_id: str) -> float:
        config = self._config(state)
        modifier = self._tree_modifier(config, strategy_id)
        value = modifier.get("base_score", modifier.get("score_bonus", 0.0))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def definitions_for_path(self, strategy_id: str):
        """Return root -> leaf definitions for inherited strategy semantics."""

        return tuple(
            self.definitions[node_id]
            for node_id in self.topology.path(strategy_id)
            if node_id in self.definitions
        )

    def primary_hands_for(self, strategy_id: str) -> tuple[str, ...]:
        values: list[str] = []
        for definition in self.definitions_for_path(strategy_id):
            for hand in definition.primary_hands:
                if hand not in values:
                    values.append(hand)
        return tuple(values)

    def _status_for_score(self, state, score: float) -> str:
        config = self._config(state)
        thresholds = (
            (MATURE, self._number(config, "mature_threshold", 16.0)),
            (COMMITTED, self._number(config, "commit_threshold", 9.0)),
            (HIGHLIGHTED, self._number(config, "highlight_threshold", 3.5)),
            (CANDIDATE, self._number(config, "candidate_threshold", 1.5)),
        )
        return next((name for name, floor in thresholds if score >= floor), AVAILABLE)

    @staticmethod
    def _raw_direct_evidence(assessment) -> float:
        effectiveness = float(assessment.effectiveness)
        if effectiveness <= 0.0:
            return 0.0
        return (float(assessment.score) - float(assessment.base_score)) / effectiveness

    def assess(self, state):
        # StateAwareBalatroStrategyTracker resolves conditional relationships here;
        # these assessments are direct-node values before topology propagation.
        direct_assessments = tuple(super().assess(state))
        direct_by_id = {
            assessment.strategy_id: assessment
            for assessment in direct_assessments
        }
        direct_evidence = {
            strategy_id: self._raw_direct_evidence(assessment)
            for strategy_id, assessment in direct_by_id.items()
        }
        node_scores = self.tree_scorer.score(direct_evidence)

        self._last_direct_assessments = MappingProxyType(direct_by_id)
        self._last_direct_evidence = MappingProxyType(dict(direct_evidence))
        self._last_tree_node_scores = node_scores

        actionable_assessments = []
        for strategy_id in sorted(
            node_id
            for node_id, node in node_scores.items()
            if node.on_frontier
        ):
            direct = direct_by_id.get(strategy_id)
            if direct is None:
                # Disabled cartridge strategies are absent from direct assessment.
                continue
            node = node_scores[strategy_id]
            if self.topology.parent_by_id[strategy_id] is None:
                # Unsplit strategies remain numerically identical to the legacy
                # tracker until their own topology is explicitly migrated. This
                # preserves positive, zero and negative conflict scores exactly.
                effective_score = float(direct.score)
            else:
                effective_score = float(direct.base_score)
                if node.active:
                    effective_score += (
                        float(node.effective_score) * float(direct.effectiveness)
                    )
            actionable_assessments.append(
                replace(
                    direct,
                    score=effective_score,
                    status=self._status_for_score(state, effective_score),
                    rationale=(
                        *direct.rationale,
                        *node.rationale,
                        f"tree direct_evidence={node.direct_evidence:.3f}",
                        f"tree foundation_score={node.foundation_score:.3f}",
                        f"tree effective_frontier_evidence={node.effective_score:.3f}",
                        f"tree on_frontier={'yes' if node.on_frontier else 'no'}",
                        f"tree active={'yes' if node.active else 'no'}",
                    ),
                )
            )

        return tuple(
            sorted(
                actionable_assessments,
                key=lambda assessment: (-assessment.score, assessment.strategy_id),
            )
        )

    def tree_node_scores(self, state=None):
        if state is not None:
            self.assess(state)
        return self._last_tree_node_scores

    def direct_evidence(self, state=None):
        if state is not None:
            self.assess(state)
        return self._last_direct_evidence

    def _branch_nodes(self, strategy_id: str) -> tuple[str, ...]:
        values: list[str] = [strategy_id]
        for child_id in self.topology.children_by_id[strategy_id]:
            values.extend(self._branch_nodes(child_id))
        return tuple(values)

    def _actionable_strategy_for_node(
        self,
        strategy_id: str,
        resolution,
        projected_scores: Mapping[str, StrategyTreeNodeScore],
    ) -> str | None:
        branch_ids = self._branch_nodes(strategy_id)
        projected_frontier = tuple(
            node_id
            for node_id in branch_ids
            if projected_scores[node_id].on_frontier
        )
        if not projected_frontier:
            return None
        current_by_id = {
            assessment.strategy_id: assessment
            for assessment in resolution.assessments
        }
        current = [
            current_by_id[node_id]
            for node_id in projected_frontier
            if node_id in current_by_id and current_by_id[node_id].score > 0.0
        ]
        if current:
            return max(current, key=lambda item: (item.score, item.strategy_id)).strategy_id

        return max(
            (projected_scores[node_id] for node_id in projected_frontier),
            key=lambda item: (item.effective_score, item.strategy_id),
        ).strategy_id

    def _projected_strategy_score(
        self,
        state,
        strategy_id: str,
        projected_scores: Mapping[str, StrategyTreeNodeScore],
    ) -> float:
        direct = self._last_direct_assessments.get(strategy_id)
        if direct is None:
            return 0.0
        node = projected_scores[strategy_id]
        value = float(direct.base_score)
        if node.on_frontier:
            value += float(node.effective_score) * float(direct.effectiveness)
        return value

    def evaluate_item(self, state, item: object, *, kind: str):
        """Tree-aware candidate alignment with legacy zero-start economics.

        Candidate relationships project through the tree for pivot detection, but
        the numeric purchase adjustment remains proportional to current positive
        strategy evidence. A candidate cannot manufacture its own strategy bonus.
        """

        kind = str(kind).upper()
        self._relationship_state = state
        resolution = self.observe(state)
        raw_relationships = super()._relationships_for(item, kind=kind)
        candidate = str(getattr(item, "name", type(item).__name__))
        if not raw_relationships:
            return StrategicItemEvaluation(
                candidate=candidate,
                kind=kind,
                strategy_id=None,
                strategy_name=None,
                tier=None,
                value=0.0,
                projected_score=0.0,
                active_alignment=False,
                pivot_candidate=False,
                rationale=("item is Neutral to every enabled universal strategy",),
            )

        projected_direct = dict(self._last_direct_evidence)
        for strategy_id, relationship in raw_relationships.items():
            if strategy_id not in projected_direct:
                continue
            projected_direct[strategy_id] += self.relationship_score(state, relationship)
        projected_scores = self.tree_scorer.score(projected_direct)

        mapped: dict[str, tuple[str, str]] = {}
        for source_strategy_id, relationship in raw_relationships.items():
            if source_strategy_id not in self.topology.nodes:
                continue
            actionable_id = self._actionable_strategy_for_node(
                source_strategy_id,
                resolution,
                projected_scores,
            )
            if actionable_id is None:
                continue
            previous = mapped.get(actionable_id)
            if previous is None or _RELATIONSHIP_PRIORITY[relationship] > _RELATIONSHIP_PRIORITY[previous[0]]:
                mapped[actionable_id] = (relationship, source_strategy_id)

        if not mapped:
            return StrategicItemEvaluation(
                candidate=candidate,
                kind=kind,
                strategy_id=None,
                strategy_name=None,
                tier=None,
                value=0.0,
                projected_score=0.0,
                active_alignment=False,
                pivot_candidate=False,
                rationale=("item has no actionable strategy relationship",),
            )

        config = self._config(state)
        pressure = self.strategy_pressure(state)
        alignment_scale = self._number(config, "candidate_alignment_scale", 0.08)
        by_id = {a.strategy_id: a for a in resolution.assessments}
        rank_by_id = {
            assessment.strategy_id: rank
            for rank, assessment in enumerate(resolution.assessments)
        }
        dominant = by_id.get(resolution.dominant_strategy_id)

        total_alignment = 0.0
        active_alignment = False
        pivot = False
        rationale: list[str] = []
        strongest_strategy_id: str | None = None
        strongest_relationship: str | None = None
        strongest_abs = -1.0
        strongest_projected = 0.0
        fallback_priority = -1
        fallback_strategy_id: str | None = None
        fallback_relationship: str | None = None
        fallback_projected = 0.0
        strongest_off_strategy_weight = 0.0

        for actionable_id, (relationship, source_strategy_id) in mapped.items():
            assessment = by_id.get(actionable_id)
            current_score = float(assessment.score) if assessment is not None else 0.0
            current_positive = max(0.0, current_score)
            scope = self._scope_factor(
                state,
                actionable_id,
                rank_by_id.get(actionable_id, 999),
                resolution,
            )
            relation_weight = self.relationship_score(state, relationship)
            contribution = 0.0
            if current_positive > 0.0 and relationship in {
                GOLD,
                SILVER,
                BRONZE,
                BANNED,
            }:
                contribution = current_positive * relation_weight * scope
            total_alignment += contribution

            projected = self._projected_strategy_score(
                state,
                actionable_id,
                projected_scores,
            )
            shortlisted = actionable_id in resolution.shortlist_strategy_ids
            if shortlisted and relationship in {GOLD, SILVER, BRONZE}:
                active_alignment = True
            elif relationship in {GOLD, SILVER, BRONZE}:
                strongest_off_strategy_weight = max(
                    strongest_off_strategy_weight,
                    relation_weight,
                )

            ante = max(1, int(getattr(state, "ante", 1) or 1))
            pivot_margin = self._number(
                config,
                "early_pivot_margin" if ante <= 5 else "late_pivot_margin",
                1.5 if ante <= 5 else 4.0,
            )
            if (
                dominant is not None
                and relationship == GOLD
                and actionable_id != dominant.strategy_id
                and projected >= float(dominant.score) + pivot_margin
            ):
                pivot = True

            positive_priority = _POSITIVE_RELATIONSHIP_PRIORITY[relationship]
            if positive_priority > fallback_priority:
                fallback_priority = positive_priority
                fallback_strategy_id = actionable_id
                fallback_relationship = relationship
                fallback_projected = projected

            if abs(contribution) > strongest_abs or (
                abs(contribution) == strongest_abs
                and _RELATIONSHIP_PRIORITY[relationship]
                > _RELATIONSHIP_PRIORITY.get(strongest_relationship or NEUTRAL, 0)
            ):
                strongest_abs = abs(contribution)
                strongest_strategy_id = actionable_id
                strongest_relationship = relationship
                strongest_projected = projected

            rationale.append(
                f"{candidate}: {relationship} at node {source_strategy_id} -> actionable {actionable_id}; "
                f"current={current_score:.3f}; projected={projected:.3f}; "
                f"scope={scope:.3f}; raw_alignment={contribution:+.3f}"
            )

        if strongest_abs <= 0.0 and fallback_relationship in {GOLD, SILVER, BRONZE}:
            strongest_strategy_id = fallback_strategy_id
            strongest_relationship = fallback_relationship
            strongest_projected = fallback_projected

        if (
            kind == "JOKER"
            and dominant is not None
            and not active_alignment
            and not pivot
            and strongest_off_strategy_weight > 0.0
        ):
            opportunity_cost = (
                max(0.0, float(dominant.score))
                * strongest_off_strategy_weight
                * self._number(config, "off_strategy_joker_penalty_factor", 1.0)
            )
            total_alignment -= opportunity_cost
            rationale.append(
                f"mapped off-strategy Joker opportunity cost=-{opportunity_cost:.3f} "
                f"against dominant {dominant.name}"
            )

        value = total_alignment * alignment_scale * pressure
        strongest_definition = self.definitions.get(strongest_strategy_id or "")
        rationale.append(
            f"strategy alignment total={total_alignment:+.3f}; scale={alignment_scale:.3f}; "
            f"Ante pressure={pressure:.3f}; purchase adjustment={value:+.3f}"
        )
        return StrategicItemEvaluation(
            candidate=candidate,
            kind=kind,
            strategy_id=strongest_strategy_id,
            strategy_name=(strongest_definition.name if strongest_definition else None),
            tier=strongest_relationship,
            value=value,
            projected_score=strongest_projected,
            active_alignment=active_alignment,
            pivot_candidate=pivot,
            rationale=tuple(rationale),
        )

    def hand_fit(self, state, hand_type: str):
        resolution = self.observe(state)
        if resolution.dominant_strategy_id is None:
            return 0.0, ("no positive universal strategy evidence",)

        hand_type = str(hand_type).upper()
        pressure = self.strategy_pressure(state)
        mapped_hand_strategy = False
        for index, strategy_id in enumerate(resolution.shortlist_strategy_ids):
            primary_hands = self.primary_hands_for(strategy_id)
            if not primary_hands:
                continue
            mapped_hand_strategy = True
            if hand_type in primary_hands:
                strength = 1.0 if index == 0 else 0.65 if index == 1 else 0.45
                return strength * pressure * self.effectiveness(state, strategy_id), (
                    f"{hand_type} reinforces shortlisted strategy "
                    f"{self.definitions[strategy_id].name}",
                )

        if not mapped_hand_strategy:
            return 0.0, ("shortlisted strategies do not prescribe a poker-hand type",)
        return -0.25 * pressure, (
            f"{hand_type} does not reinforce a shortlisted poker-hand strategy",
        )
