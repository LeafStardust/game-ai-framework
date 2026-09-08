from __future__ import annotations

import math
from dataclasses import dataclass

from games.balatro.consumable import Consumable
from games.balatro.state import BalatroState

from .effects import (
    CONSUMABLE_GENERATE,
    DECK_REMOVE,
    DECK_TRANSFORM,
    ECONOMY,
    HAND_LEVEL,
    HELD_EFFECT,
    JOKER_GENERATE,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    ConsumableBehaviorAnalyzer,
    EffectDescriptor,
)
from .profile import BalatroBuildProfiler, BuildProfile
from .synergy import BuildSynergyWeights, SynergyContribution


@dataclass(frozen=True)
class ConsumableBuildPathWeights:
    """Structural weights for B4 prospective build-path reasoning.

    These values are deliberately not prices or final shop utilities. B4 answers
    whether a consumable creates something the current build can exploit; D4/D5
    later combine that signal with money, slot pressure, timing and target quality.
    """

    requirement_enable: float = 1.00
    requirement_reinforce: float = 0.40
    scaling_source: float = 0.60
    amplifier_source: float = 0.90
    prospective_source: float = 0.30
    downstream_value_multiplier: float = 0.35


@dataclass(frozen=True)
class ConsumableBuildPath:
    source_feature: str
    derived_feature: str
    consumer: str
    relationship: str
    downstream_features: tuple[str, ...]
    amount: float
    detail: str


@dataclass(frozen=True)
class ContextualConsumableEvaluation:
    candidate: str
    descriptor: EffectDescriptor
    intrinsic_gain: float
    build_path_gain: float
    total_gain: float
    realized_features: tuple[str, ...]
    prospective_features: tuple[str, ...]
    paths: tuple[ConsumableBuildPath, ...]
    contributions: tuple[SynergyContribution, ...]

    @property
    def rationale(self) -> tuple[str, ...]:
        return tuple(contribution.detail for contribution in self.contributions) + tuple(
            path.detail for path in self.paths
        )


class BuildFeatureClosure:
    """Expand an observable transformation into conservative future-use features.

    The closure never predicts a draw. It only states what a transformed public
    deck card *can* be when drawn later. Rank/suit/enhancement/seal transformations
    therefore expose their held-card form as prospective capability. Known held
    effect sources are promoted to ``held:effect`` so generic amplifiers such as
    Mime can match them without a Joker-pair lookup table.
    """

    HELD_EFFECT_ENHANCEMENTS = frozenset({"Steel", "Gold"})
    HELD_EFFECT_SEALS = frozenset({"Blue"})

    def expand(self, features: set[str] | frozenset[str]) -> dict[str, str]:
        derived: dict[str, str] = {feature: feature for feature in features}

        for feature in tuple(features):
            if feature.startswith("rank:"):
                derived[f"held:{feature}"] = feature
            elif feature.startswith("suit:"):
                derived[f"held:{feature}"] = feature
            elif feature.startswith("enhancement:"):
                derived[f"held:{feature}"] = feature
                enhancement = feature.split(":", 1)[1]
                if enhancement in self.HELD_EFFECT_ENHANCEMENTS:
                    derived[HELD_EFFECT] = feature
            elif feature.startswith("seal:"):
                derived[f"held:{feature}"] = feature
                seal = feature.split(":", 1)[1]
                if seal in self.HELD_EFFECT_SEALS:
                    derived[HELD_EFFECT] = feature

        return derived


class ContextualConsumableSynergyEvaluator:
    """Evaluate a consumable as a prospective transition of the whole build.

    B4 consumes the behavior-backed descriptor from B1 and the current public
    ``BuildProfile`` from B2. It does not choose an exact live target and does not
    decide whether to spend money. Instead it exposes why a transformation is
    valuable to existing engines so D4/D5/D6/D9 can reuse the same reasoning.
    """

    def __init__(
        self,
        *,
        base_weights: BuildSynergyWeights | None = None,
        path_weights: ConsumableBuildPathWeights | None = None,
        profiler: BalatroBuildProfiler | None = None,
        analyzer: ConsumableBehaviorAnalyzer | None = None,
        closure: BuildFeatureClosure | None = None,
    ) -> None:
        self.base_weights = base_weights or BuildSynergyWeights()
        self.path_weights = path_weights or ConsumableBuildPathWeights()
        self.analyzer = analyzer or ConsumableBehaviorAnalyzer()
        self.profiler = profiler or BalatroBuildProfiler(consumable_analyzer=self.analyzer)
        self.closure = closure or BuildFeatureClosure()

    def evaluate(
        self,
        candidate: object,
        state: BalatroState,
        *,
        profile: BuildProfile | None = None,
    ) -> ContextualConsumableEvaluation:
        build = profile or self.profiler.profile(state)
        if not isinstance(candidate, Consumable):
            descriptor = EffectDescriptor(source=type(candidate).__name__, kind="UNKNOWN")
            return ContextualConsumableEvaluation(
                candidate=type(candidate).__name__,
                descriptor=descriptor,
                intrinsic_gain=0.0,
                build_path_gain=0.0,
                total_gain=0.0,
                realized_features=(),
                prospective_features=(),
                paths=(),
                contributions=(),
            )

        descriptor = self.analyzer.describe(candidate, state=state)
        contributions: list[SynergyContribution] = []
        intrinsic_gain = self._intrinsic_gain(descriptor, contributions)

        source_features = set(descriptor.produces) | set(descriptor.transforms)
        closure = self.closure.expand(source_features)
        prospective_features = set(closure) - source_features
        paths: list[ConsumableBuildPath] = []
        seen_paths: set[tuple[str, str, str]] = set()

        for consumer in build.descriptors(kind="JOKER"):
            downstream = tuple(sorted(self._downstream_features(consumer)))
            downstream_value = self._downstream_value(consumer)

            for feature, source_feature in sorted(closure.items()):
                relationship: str | None = None
                base_amount = 0.0

                if feature in consumer.requires:
                    already_present = self._context_strength(build, feature) > 0.0
                    relationship = (
                        "REINFORCES_REQUIREMENT" if already_present else "ENABLES_REQUIREMENT"
                    )
                    base_amount = (
                        self.path_weights.requirement_reinforce
                        if already_present
                        else self.path_weights.requirement_enable
                    )
                elif feature in consumer.scales_with:
                    relationship = "ADDS_SCALING_SOURCE"
                    current_strength = self._context_strength(build, feature)
                    base_amount = self.path_weights.scaling_source / math.sqrt(
                        1.0 + current_strength
                    )
                elif feature in consumer.amplifies:
                    relationship = "AMPLIFIED_BY_BUILD"
                    base_amount = self.path_weights.amplifier_source

                if relationship is None:
                    continue

                key = (feature, consumer.source, relationship)
                if key in seen_paths:
                    continue
                seen_paths.add(key)

                amount = base_amount + (
                    self.path_weights.downstream_value_multiplier * downstream_value
                )
                paths.append(
                    ConsumableBuildPath(
                        source_feature=source_feature,
                        derived_feature=feature,
                        consumer=consumer.source,
                        relationship=relationship,
                        downstream_features=downstream,
                        amount=amount,
                        detail=(
                            f"{descriptor.source} creates {source_feature} -> {feature}; "
                            f"{relationship.lower().replace('_', ' ')} for {consumer.source} "
                            f"(+{amount:.3f})"
                        ),
                    )
                )

        # A prospective transformation that is not yet tied to a known engine is
        # retained at small positive value instead of being treated as worthless.
        # This lets later build-intent logic reason about setup pieces while still
        # strongly preferring transformations with demonstrated downstream use.
        used_sources = {path.source_feature for path in paths}
        for feature in sorted(descriptor.transforms - used_sources):
            amount = self.path_weights.prospective_source
            contributions.append(
                SynergyContribution(
                    kind="PROSPECTIVE_TRANSFORM",
                    feature=feature,
                    amount=amount,
                    source=descriptor.source,
                    detail=f"prospective deck feature {feature} (+{amount:.3f})",
                )
            )

        build_path_gain = sum(path.amount for path in paths) + sum(
            contribution.amount
            for contribution in contributions
            if contribution.kind == "PROSPECTIVE_TRANSFORM"
        )
        total_gain = intrinsic_gain + build_path_gain
        return ContextualConsumableEvaluation(
            candidate=str(getattr(candidate, "name", type(candidate).__name__)),
            descriptor=descriptor,
            intrinsic_gain=intrinsic_gain,
            build_path_gain=build_path_gain,
            total_gain=total_gain,
            realized_features=tuple(sorted(source_features)),
            prospective_features=tuple(sorted(prospective_features)),
            paths=tuple(paths),
            contributions=tuple(contributions),
        )

    def rank(
        self,
        candidates: list[object] | tuple[object, ...],
        state: BalatroState,
        *,
        profile: BuildProfile | None = None,
    ) -> tuple[ContextualConsumableEvaluation, ...]:
        build = profile or self.profiler.profile(state)
        evaluations = [
            self.evaluate(candidate, state, profile=build)
            for candidate in candidates
        ]
        return tuple(
            sorted(
                evaluations,
                key=lambda evaluation: (-evaluation.total_gain, evaluation.candidate),
            )
        )

    def _intrinsic_gain(
        self,
        descriptor: EffectDescriptor,
        contributions: list[SynergyContribution],
    ) -> float:
        total = 0.0
        for feature in sorted(set(descriptor.produces) | set(descriptor.transforms)):
            amount = self._feature_value(feature)
            if amount <= 0.0:
                continue
            total += amount
            contributions.append(
                SynergyContribution(
                    kind="INTRINSIC",
                    feature=feature,
                    amount=amount,
                    source=descriptor.source,
                    detail=f"intrinsic {feature} (+{amount:.3f})",
                )
            )
        return total

    def _downstream_value(self, descriptor: EffectDescriptor) -> float:
        return sum(self._feature_value(feature) for feature in self._downstream_features(descriptor))

    @staticmethod
    def _downstream_features(descriptor: EffectDescriptor) -> frozenset[str]:
        return frozenset(set(descriptor.produces) | set(descriptor.transforms))

    def _context_strength(self, build: BuildProfile, feature: str) -> float:
        direct = build.strength(feature)
        if feature.startswith("held:") and feature != HELD_EFFECT:
            return max(direct, build.strength(feature[len("held:") :]))
        return direct

    def _feature_value(self, feature: str) -> float:
        weights = self.base_weights
        explicit = {
            SCORE_CHIPS: weights.score_chips,
            SCORE_MULT: weights.score_mult,
            SCORE_XMULT: weights.score_xmult,
            ECONOMY: weights.economy,
            HAND_LEVEL: weights.hand_level,
            DECK_TRANSFORM: weights.deck_transform,
            DECK_REMOVE: weights.deck_remove,
            JOKER_GENERATE: weights.joker_generate,
            CONSUMABLE_GENERATE: weights.consumable_generate,
            HELD_EFFECT: 0.0,
        }
        if feature in explicit:
            return explicit[feature]
        if feature.startswith(
            (
                "rank:",
                "suit:",
                "enhancement:",
                "seal:",
                "edition:",
                "hand:",
                "consumable:",
            )
        ):
            return weights.generic_structural_output
        return 0.0
