from __future__ import annotations

from dataclasses import dataclass

from .effects import (
    CONSUMABLE_GENERATE,
    ECONOMY,
    HAND_LEVEL,
    JOKER_GENERATE,
    EffectDescriptor,
)
from .joker_lifecycle import (
    STATEFUL_ACTIVATION,
    STATEFUL_DECAY,
    STATEFUL_SCALING,
    LifecycleJokerBehaviorAnalyzer,
)
from .joker_semantics import (
    CARD_GENERATE,
    CONSUMABLE_DUPLICATE,
    DEBT_CAPACITY,
    DISCARDS_RESOURCE,
    FREE_REROLL_RESOURCE,
    HAND_SIZE_RESOURCE,
    HANDS_RESOURCE,
    SELL_VALUE_GROWTH,
    SHOP_DISCOUNT,
    SemanticEffectDescriptor,
    SemanticJokerBehaviorAnalyzer,
)
from .profile import BalatroBuildProfiler
from .synergy import (
    BuildSynergyWeights,
    ContextualJokerSynergyEvaluator,
    JokerPairInteractionProbe,
    SynergyContribution,
)


@dataclass(frozen=True)
class JokerSemanticValueWeights:
    """Structural values for non-scoring and lifecycle Joker capabilities.

    These remain build-intelligence units, not shop dollars. D2 applies price,
    interest, reserve and slot economics after this contextual value is produced.
    """

    hands: float = 0.90
    discards: float = 0.65
    hand_size: float = 0.75
    free_reroll: float = 0.75
    card_generate: float = 0.60
    consumable_duplicate: float = 1.00
    sell_value_growth: float = 0.35
    shop_discount: float = 0.75
    debt_capacity: float = 0.15
    stateful_activation: float = 0.35
    stateful_scaling: float = 1.25
    stateful_decay: float = 0.75


class SemanticContextualJokerSynergyEvaluator(ContextualJokerSynergyEvaluator):
    """B3 evaluator extended with non-scoring gains and persistent tradeoffs."""

    MAGNITUDE_SCALED_FEATURES = frozenset(
        {
            ECONOMY,
            HAND_LEVEL,
            JOKER_GENERATE,
            CONSUMABLE_GENERATE,
            HANDS_RESOURCE,
            DISCARDS_RESOURCE,
            HAND_SIZE_RESOURCE,
            FREE_REROLL_RESOURCE,
            CARD_GENERATE,
            CONSUMABLE_DUPLICATE,
            SELL_VALUE_GROWTH,
            SHOP_DISCOUNT,
            DEBT_CAPACITY,
        }
    )

    def __init__(
        self,
        *,
        weights: BuildSynergyWeights | None = None,
        semantic_weights: JokerSemanticValueWeights | None = None,
        profiler: BalatroBuildProfiler | None = None,
        joker_analyzer: SemanticJokerBehaviorAnalyzer | None = None,
        pair_probe: JokerPairInteractionProbe | None = None,
    ) -> None:
        analyzer = joker_analyzer or LifecycleJokerBehaviorAnalyzer()
        build_profiler = profiler or BalatroBuildProfiler(joker_analyzer=analyzer)
        self.semantic_weights = semantic_weights or JokerSemanticValueWeights()
        super().__init__(
            weights=weights,
            profiler=build_profiler,
            joker_analyzer=analyzer,
            pair_probe=pair_probe,
        )

    def _intrinsic_gain(
        self,
        descriptor: EffectDescriptor,
        contributions: list[SynergyContribution] | None = None,
    ) -> float:
        total = 0.0
        semantic = descriptor if isinstance(descriptor, SemanticEffectDescriptor) else None

        for feature in sorted(self._effective_features(descriptor)):
            unit = self._feature_value(feature)
            if unit <= 0.0:
                continue
            magnitude = (
                semantic.feature_magnitude(feature)
                if semantic is not None and feature in self.MAGNITUDE_SCALED_FEATURES
                else 1.0
            )
            amount = unit * self._bounded_magnitude(magnitude)
            total += amount
            if contributions is not None:
                contributions.append(
                    SynergyContribution(
                        kind="INTRINSIC",
                        feature=feature,
                        amount=amount,
                        source=descriptor.source,
                        detail=(
                            f"intrinsic {feature} magnitude={magnitude:.3f} "
                            f"(+{amount:.3f})"
                        ),
                    )
                )

        if semantic is not None:
            for feature in sorted(semantic.penalizes):
                unit = self._feature_value(feature)
                if unit <= 0.0:
                    continue
                magnitude = semantic.penalty_magnitude(feature)
                amount = unit * self._bounded_magnitude(magnitude)
                total -= amount
                if contributions is not None:
                    contributions.append(
                        SynergyContribution(
                            kind="INTRINSIC_PENALTY",
                            feature=feature,
                            amount=-amount,
                            source=descriptor.source,
                            detail=(
                                f"penalizes {feature} magnitude={magnitude:.3f} "
                                f"(-{amount:.3f})"
                            ),
                        )
                    )

        return total

    def _feature_value(self, feature: str) -> float:
        semantic = self.semantic_weights
        explicit = {
            HANDS_RESOURCE: semantic.hands,
            DISCARDS_RESOURCE: semantic.discards,
            HAND_SIZE_RESOURCE: semantic.hand_size,
            FREE_REROLL_RESOURCE: semantic.free_reroll,
            CARD_GENERATE: semantic.card_generate,
            CONSUMABLE_DUPLICATE: semantic.consumable_duplicate,
            SELL_VALUE_GROWTH: semantic.sell_value_growth,
            SHOP_DISCOUNT: semantic.shop_discount,
            DEBT_CAPACITY: semantic.debt_capacity,
            STATEFUL_ACTIVATION: semantic.stateful_activation,
            STATEFUL_SCALING: semantic.stateful_scaling,
            STATEFUL_DECAY: semantic.stateful_decay,
        }
        if feature in explicit:
            return explicit[feature]
        return super()._feature_value(feature)

    @staticmethod
    def _bounded_magnitude(value: float) -> float:
        # Magnitudes are evidence strength, not an invitation for unbounded utility.
        # Resource effects above four units retain value but are softly capped so a
        # single large modeled signal cannot dominate every other build component.
        return min(4.0, max(1.0, float(value)))
