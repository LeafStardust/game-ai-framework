from games.balatro.build.effects import (
    CONSUMABLE_GENERATE,
    ECONOMY,
    HAND_LEVEL,
    JOKER_GENERATE,
    consumable_category_feature,
    hand_feature,
    rank_feature,
)
from games.balatro.build.joker_semantics import (
    DISCARDS_RESOURCE,
    HAND_SIZE_RESOURCE,
    HANDS_RESOURCE,
    SELL_VALUE_GROWTH,
    SemanticEffectDescriptor,
    SemanticJokerBehaviorAnalyzer,
)
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.semantic_synergy import SemanticContextualJokerSynergyEvaluator
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.cartomancer import CartomancerJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.hallucination import HallucinationJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.riff_raff import RiffRaffJoker
from games.balatro.jokers.space_joker import SpaceJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


def test_superposition_promotes_generated_tarot_semantics_and_conditions():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(SuperpositionJoker())

    assert isinstance(descriptor, SemanticEffectDescriptor)
    assert CONSUMABLE_GENERATE in descriptor.produces
    assert consumable_category_feature("TAROT") in descriptor.produces
    assert hand_feature("STRAIGHT") in descriptor.requires
    assert rank_feature("A") in descriptor.requires


def test_event_driven_consumable_generation_is_discovered():
    analyzer = SemanticJokerBehaviorAnalyzer()

    cartomancer = analyzer.describe(CartomancerJoker())
    hallucination = analyzer.describe(HallucinationJoker())

    assert CONSUMABLE_GENERATE in cartomancer.produces
    assert CONSUMABLE_GENERATE in hallucination.produces
    assert consumable_category_feature("TAROT") in hallucination.produces


def test_riff_raff_exposes_two_joker_generation_capability():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(RiffRaffJoker())

    assert JOKER_GENERATE in descriptor.produces
    assert descriptor.feature_magnitude(JOKER_GENERATE) == 2.0


def test_round_end_economy_uses_context_money_channel():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(GoldenJoker())

    assert ECONOMY in descriptor.produces
    assert descriptor.feature_magnitude(ECONOMY) == 4.0


def test_probabilistic_hand_level_capability_is_found_deterministically():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(SpaceJoker())

    assert HAND_LEVEL in descriptor.produces
    assert "context:level_ups" in descriptor.evidence


def test_hand_size_resource_is_semantic_not_opaque_signal():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(JugglerJoker())

    assert HAND_SIZE_RESOURCE in descriptor.produces
    assert descriptor.feature_magnitude(HAND_SIZE_RESOURCE) == 1.0


def test_burglar_records_hands_gain_and_discard_loss_separately():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(BurglarJoker())

    assert HANDS_RESOURCE in descriptor.produces
    assert descriptor.feature_magnitude(HANDS_RESOURCE) == 3.0
    assert DISCARDS_RESOURCE in descriptor.penalizes
    assert descriptor.penalty_magnitude(DISCARDS_RESOURCE) == 3.0


def test_troubadour_records_both_sides_of_resource_tradeoff():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(TroubadourJoker())

    assert HAND_SIZE_RESOURCE in descriptor.produces
    assert descriptor.feature_magnitude(HAND_SIZE_RESOURCE) == 2.0
    assert HANDS_RESOURCE in descriptor.penalizes
    assert descriptor.penalty_magnitude(HANDS_RESOURCE) == 1.0


def test_self_sell_value_growth_is_discovered_from_real_joker_mutation():
    descriptor = SemanticJokerBehaviorAnalyzer().describe(EggJoker())

    assert SELL_VALUE_GROWTH in descriptor.produces
    assert descriptor.feature_magnitude(SELL_VALUE_GROWTH) == 3.0


def test_semantic_evaluator_assigns_nonzero_intrinsic_value_to_superposition():
    state = BalatroState()
    evaluator = SemanticContextualJokerSynergyEvaluator()

    value = evaluator.evaluate(SuperpositionJoker(), state)

    assert value.intrinsic_gain > 0.0
    assert any(
        contribution.feature == CONSUMABLE_GENERATE
        and contribution.amount > 0.0
        for contribution in value.contributions
    )


def test_semantic_evaluator_subtracts_explicit_resource_penalties():
    state = BalatroState()
    evaluator = SemanticContextualJokerSynergyEvaluator()

    value = evaluator.evaluate(BurglarJoker(), state)

    assert any(
        contribution.kind == "INTRINSIC_PENALTY"
        and contribution.feature == DISCARDS_RESOURCE
        and contribution.amount < 0.0
        for contribution in value.contributions
    )


def test_default_joker_build_value_uses_semantic_contextual_evaluator():
    state = BalatroState()
    value = JokerBuildValueEvaluator().evaluate(state, SuperpositionJoker())

    assert value.direct_scoring_gain == 0.0
    assert value.contextual.intrinsic_gain > 0.0
    assert value.total_gain > value.contextual.interaction_gain
