from games.balatro.build.effects import (
    DECK_REMOVE,
    DECK_TRANSFORM,
    HAND_LEVEL,
    HELD_EFFECT,
    HELD_RETRIGGER,
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    TARGET_CARD,
    ConsumableBehaviorAnalyzer,
    JokerBehaviorAnalyzer,
    describe_build_item,
    enhancement_feature,
    hand_feature,
    rank_feature,
)
from games.balatro.card import BalatroCard
from games.balatro.consumable import PlanetCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot, HangedMan


def test_baron_effect_inference_uses_real_held_king_behavior():
    descriptor = JokerBehaviorAnalyzer().describe(BaronJoker())

    assert descriptor.kind == "JOKER"
    assert SCORE_XMULT in descriptor.produces
    assert rank_feature("K", held=True) in descriptor.requires
    assert rank_feature("K", held=True) in descriptor.scales_with
    assert rank_feature("K") not in descriptor.requires


def test_fibonacci_inference_only_credits_positive_rank_scaling():
    descriptor = JokerBehaviorAnalyzer().describe(FibonacciJoker())

    expected = {
        rank_feature("A"),
        rank_feature("2"),
        rank_feature("3"),
        rank_feature("5"),
        rank_feature("8"),
    }
    assert descriptor.scales_with == frozenset(expected)
    assert rank_feature("4") not in descriptor.scales_with
    assert rank_feature("10") not in descriptor.scales_with
    assert rank_feature("K") not in descriptor.scales_with


def test_superposition_inference_discovers_straight_and_ace_conjunction():
    descriptor = JokerBehaviorAnalyzer().describe(SuperpositionJoker())

    straight = hand_feature("STRAIGHT")
    ace = rank_feature("A")
    assert straight in descriptor.requires
    assert straight in descriptor.scales_with
    assert ace in descriptor.requires
    assert ace in descriptor.scales_with
    assert rank_feature("K") not in descriptor.requires
    assert rank_feature("K") not in descriptor.scales_with
    assert "context:created_tarot_cards" in descriptor.evidence


def test_mime_effect_inference_exposes_held_retrigger_synergy():
    descriptor = JokerBehaviorAnalyzer().describe(MimeJoker())

    assert HELD_RETRIGGER in descriptor.produces
    assert HELD_EFFECT in descriptor.amplifies
    assert "context:retrigger_held_abilities" in descriptor.evidence


def test_unknown_item_does_not_receive_fabricated_semantics():
    descriptor = describe_build_item(object())

    assert descriptor.kind == "UNKNOWN"
    assert descriptor.produces == frozenset()
    assert descriptor.requires == frozenset()
    assert descriptor.amplifies == frozenset()
    assert descriptor.transforms == frozenset()


def test_planet_descriptor_records_hand_specific_scaling():
    planet = PlanetCard("Test Planet", "PAIR", chips=15, mult=2)
    descriptor = ConsumableBehaviorAnalyzer().describe(planet)

    assert descriptor.kind == "CONSUMABLE"
    assert HAND_LEVEL in descriptor.produces
    assert SCORE_CHIPS in descriptor.produces
    assert SCORE_MULT in descriptor.produces
    assert hand_feature("PAIR") in descriptor.produces


def test_chariot_descriptor_detects_real_steel_transformation_without_mutating_state():
    state = BalatroState()
    state.hand = [BalatroCard("K", "Hearts")]

    descriptor = ConsumableBehaviorAnalyzer().describe(Chariot(), state=state)

    steel = enhancement_feature("Steel")
    assert descriptor.kind == "CONSUMABLE"
    assert DECK_TRANSFORM in descriptor.produces
    assert steel in descriptor.produces
    assert steel in descriptor.transforms
    assert TARGET_CARD in descriptor.requires
    assert state.hand[0].enhancement is None


def test_destructive_consumable_does_not_infer_positional_card_transformations():
    state = BalatroState()
    state.hand = [
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("9", "Clubs"),
    ]

    descriptor = ConsumableBehaviorAnalyzer().describe(HangedMan(), state=state)

    assert DECK_REMOVE in descriptor.produces
    assert DECK_TRANSFORM not in descriptor.produces
    assert descriptor.transforms == frozenset()
    assert len(state.hand) == 3
