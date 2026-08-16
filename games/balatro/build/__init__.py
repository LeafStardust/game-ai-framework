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
    """Use the phase-aware base probe without treating probe inputs as outputs.

    The semantic hierarchy previously forced every conditional probe through
    ``HAND_SCORED``.  The phase-aware base probe is required for held/played-card
    Jokers, but its per-card probes seed ``played_card`` / ``held_card`` in
    ``context.data``.  Those are probe inputs, not Joker-produced capabilities, so
    strip them from the merged result.

    The Duo and similar hand-shape Jokers inspect the actual cards rather than only
    ``context.poker_hand``.  Give the neutral Pair condition probe a real Pair so
    generic hand-feature inference observes the same condition production uses.
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

    result = JokerBehaviorAnalyzer._probe(
        self,
        joker,
        cards=probe_cards,
        held_cards=held_cards,
        poker_hand=poker_hand,
    )
    ignored_features = {"signal:played_card", "signal:held_card"}
    ignored_evidence = {"context:played_card", "context:held_card"}
    return type(result)(
        magnitudes=tuple(
            (feature, amount)
            for feature, amount in result.magnitudes
            if feature not in ignored_features
        ),
        evidence=tuple(
            item for item in result.evidence if item not in ignored_evidence
        ),
        amplifies=result.amplifies,
    )


# Reuse the phase-aware conditional probe through the semantic/lifecycle/scenario
# hierarchy while preserving clean semantic output.
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
