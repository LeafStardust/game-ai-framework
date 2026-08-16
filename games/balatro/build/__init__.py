from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand

from .consumable_synergy import (
    BuildFeatureClosure,
    ConsumableBuildPath,
    ConsumableBuildPathWeights,
    ContextualConsumableEvaluation,
    ContextualConsumableSynergyEvaluator,
)
from .consumable_targeting import (
    ConsumableTargetEvaluation,
    ContextualConsumableTargetEvaluator,
)
from .effects import (
    CONSUMABLE_GENERATE,
    DECK_REMOVE,
    DECK_TRANSFORM,
    ECONOMY,
    HAND_LEVEL,
    HELD_EFFECT,
    HELD_RETRIGGER,
    JOKER_GENERATE,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    TARGET_CARD,
    ConsumableBehaviorAnalyzer,
    EffectDescriptor,
    JokerBehaviorAnalyzer,
    describe_build_item,
    edition_feature,
    enhancement_feature,
    hand_feature,
    rank_feature,
    seal_feature,
    suit_feature,
)
from .joker_lifecycle import (
    STATEFUL_ACTIVATION,
    STATEFUL_DECAY,
    STATEFUL_SCALING,
    LifecycleJokerBehaviorAnalyzer,
    lifecycle_event_feature,
)
from .joker_scenarios import (
    BOSS_CONTROL,
    CARD_RULE,
    DUPLICATE_PERMISSION,
    HAND_RULE,
    JOKER_COPY,
    JOKER_DESTROY,
    PERMANENT_CARD_GROWTH,
    PLAYED_RETRIGGER,
    PROBABILITY_MULTIPLIER,
    SELF_DESTRUCT,
    SURVIVAL,
    TAG_GENERATE,
    ScenarioJokerBehaviorAnalyzer,
    scenario_feature,
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
from .joker_strategy import (
    JokerBuildTransition,
    JokerBuildTransitionPlanner,
    JokerBuildValue,
    JokerBuildValueEvaluator,
    JokerBuildValueWeights,
    JokerReplacementOption,
)
from .playing_card_synergy import (
    ContextualPlayingCardEvaluation,
    ContextualPlayingCardSynergyEvaluator,
)
from .profile import BalatroBuildProfiler, BuildProfile
from .semantic_synergy import (
    JokerSemanticValueWeights,
    SemanticContextualJokerSynergyEvaluator,
)
from .synergy import (
    BuildSynergyWeights,
    ContextualBuildEvaluation,
    ContextualJokerSynergyEvaluator,
    JokerPairInteraction,
    JokerPairInteractionProbe,
    SynergyContribution,
)


def _semantic_phase_probe(
    self,
    joker,
    *,
    cards,
    held_cards,
    poker_hand=PokerHand.HIGH_CARD,
):
    """Run conditional discovery across scoring phases with semantic outputs.

    The semantic hierarchy must preserve the higher-level interpretation performed
    by ``_run_semantic_probe`` (for example ``created_consumables`` becoming
    ``consumable:generate``) while also observing phase-specific held/played-card
    Joker behavior. Per-card probes still use the low-level trigger helper because
    those callbacks require an explicit ``played_card`` / ``held_card`` input.
    """
    probe_cards = cards
    if poker_hand is PokerHand.PAIR and cards == JokerBehaviorAnalyzer._neutral_cards():
        probe_cards = [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
            BalatroCard("Q", "Clubs"),
            BalatroCard("9", "Diamonds"),
            BalatroCard("2", "Spades"),
        ]

    probes = [
        self._run_semantic_probe(
            joker,
            cards=probe_cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="",
            random_seed=0,
        ),
        self._run_semantic_probe(
            joker,
            cards=probe_cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="HAND_SCORED",
            random_seed=0,
        ),
        self._run_semantic_probe(
            joker,
            cards=probe_cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="HAND_PLAYED",
            random_seed=0,
        ),
    ]
    probes.extend(
        JokerBehaviorAnalyzer._probe_trigger(
            joker,
            cards=probe_cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="PLAYED_CARD",
            data={"played_card": card},
        )
        for card in probe_cards
    )
    probes.extend(
        JokerBehaviorAnalyzer._probe_trigger(
            joker,
            cards=probe_cards,
            held_cards=held_cards,
            poker_hand=poker_hand,
            trigger="HELD_CARD",
            data={"held_card": card},
        )
        for card in held_cards
    )

    ignored_features = {"signal:played_card", "signal:held_card"}
    ignored_evidence = {"context:played_card", "context:held_card"}
    magnitudes: dict[str, float] = {}
    penalties: dict[str, float] = {}
    evidence: set[str] = set()
    amplifies: set[str] = set()

    for result in probes:
        amplifies.update(result.amplifies)
        evidence.update(
            item for item in result.evidence if item not in ignored_evidence
        )
        for feature, amount in result.magnitudes:
            if feature in ignored_features:
                continue
            magnitudes[feature] = max(magnitudes.get(feature, 0.0), amount)
        for feature, amount in getattr(result, "penalties", ()):
            penalties[feature] = max(penalties.get(feature, 0.0), amount)

    return type(probes[0])(
        magnitudes=tuple(sorted(magnitudes.items())),
        penalties=tuple(sorted(penalties.items())),
        evidence=tuple(sorted(evidence)),
        amplifies=frozenset(amplifies),
    )


# Reuse the phase-aware semantic probe through the semantic/lifecycle/scenario
# hierarchy without downgrading semantic context outputs to raw signal features.
SemanticJokerBehaviorAnalyzer._probe = _semantic_phase_probe

__all__ = [
    "BOSS_CONTROL",
    "BalatroBuildProfiler",
    "BuildFeatureClosure",
    "BuildProfile",
    "BuildSynergyWeights",
    "CARD_GENERATE",
    "CARD_RULE",
    "CONSUMABLE_DUPLICATE",
    "CONSUMABLE_GENERATE",
    "ConsumableBehaviorAnalyzer",
    "ConsumableBuildPath",
    "ConsumableBuildPathWeights",
    "ConsumableTargetEvaluation",
    "ContextualBuildEvaluation",
    "ContextualConsumableEvaluation",
    "ContextualConsumableSynergyEvaluator",
    "ContextualConsumableTargetEvaluator",
    "ContextualJokerSynergyEvaluator",
    "ContextualPlayingCardEvaluation",
    "ContextualPlayingCardSynergyEvaluator",
    "DEBT_CAPACITY",
    "DECK_REMOVE",
    "DECK_TRANSFORM",
    "DISCARDS_RESOURCE",
    "DUPLICATE_PERMISSION",
    "ECONOMY",
    "EffectDescriptor",
    "FREE_REROLL_RESOURCE",
    "HAND_LEVEL",
    "HAND_RULE",
    "HAND_SIZE_RESOURCE",
    "HANDS_RESOURCE",
    "HELD_EFFECT",
    "HELD_RETRIGGER",
    "JOKER_COPY",
    "JOKER_DESTROY",
    "JOKER_GENERATE",
    "JokerBehaviorAnalyzer",
    "JokerBuildTransition",
    "JokerBuildTransitionPlanner",
    "JokerBuildValue",
    "JokerBuildValueEvaluator",
    "JokerBuildValueWeights",
    "JokerPairInteraction",
    "JokerPairInteractionProbe",
    "JokerReplacementOption",
    "JokerSemanticValueWeights",
    "LifecycleJokerBehaviorAnalyzer",
    "PERMANENT_CARD_GROWTH",
    "PLAYED_RETRIGGER",
    "PROBABILITY_MULTIPLIER",
    "SCORE_CHIPS",
    "SCORE_MULT",
    "SCORE_XMULT",
    "SELF_DESTRUCT",
    "SELL_VALUE_GROWTH",
    "SHOP_DISCOUNT",
    "STATEFUL_ACTIVATION",
    "STATEFUL_DECAY",
    "STATEFUL_SCALING",
    "SURVIVAL",
    "ScenarioJokerBehaviorAnalyzer",
    "SemanticContextualJokerSynergyEvaluator",
    "SemanticEffectDescriptor",
    "SemanticJokerBehaviorAnalyzer",
    "SynergyContribution",
    "TAG_GENERATE",
    "TARGET_CARD",
    "describe_build_item",
    "edition_feature",
    "enhancement_feature",
    "hand_feature",
    "lifecycle_event_feature",
    "rank_feature",
    "scenario_feature",
    "seal_feature",
    "suit_feature",
]
