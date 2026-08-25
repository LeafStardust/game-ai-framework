from games.balatro.build import HELD_EFFECT, ContextualJokerSynergyEvaluator
from games.balatro.build.effects import hand_feature, rank_feature
from games.balatro.card import BalatroCard
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.state import BalatroState


def _deck_with_kings(count: int) -> list[BalatroCard]:
    cards = [
        BalatroCard("K", ("Hearts", "Diamonds", "Clubs", "Spades")[index % 4])
        for index in range(count)
    ]
    cards.extend(
        BalatroCard("Q", "Hearts")
        for _ in range(max(0, 8 - count))
    )
    return cards


def test_baron_context_gain_increases_when_public_deck_contains_kings():
    evaluator = ContextualJokerSynergyEvaluator()

    poor = BalatroState()
    poor.deck = _deck_with_kings(0)
    rich = BalatroState()
    rich.deck = _deck_with_kings(4)

    poor_value = evaluator.evaluate(BaronJoker(), poor)
    rich_value = evaluator.evaluate(BaronJoker(), rich)

    assert rich_value.intrinsic_gain == poor_value.intrinsic_gain
    assert rich_value.intrinsic_gain > 0.0
    assert "held:rank:K" in poor_value.unmet_requirements
    assert "held:rank:K" in rich_value.matched_requirements
    assert "held:rank:K" in rich_value.matched_scaling
    assert rich_value.interaction_gain > poor_value.interaction_gain
    assert rich_value.total_gain > poor_value.total_gain


def test_fibonacci_context_only_matches_actual_fibonacci_ranks():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()
    suits = ("Hearts", "Diamonds", "Clubs", "Spades")
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    state.deck = [
        BalatroCard(rank, suit)
        for rank in ranks
        for suit in suits
    ]

    value = evaluator.evaluate(FibonacciJoker(), state)

    assert set(value.matched_scaling) == {
        rank_feature("A"),
        rank_feature("2"),
        rank_feature("3"),
        rank_feature("5"),
        rank_feature("8"),
    }
    assert rank_feature("4") not in value.matched_scaling
    assert rank_feature("10") not in value.matched_scaling
    assert rank_feature("K") not in value.matched_scaling


def test_superposition_requires_ace_without_default_straight_specialization():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()

    value = evaluator.evaluate(SuperpositionJoker(), state)

    ace = rank_feature("A")
    straight = hand_feature("STRAIGHT")
    assert ace in value.matched_requirements
    assert ace in value.matched_scaling
    assert straight not in value.matched_requirements
    assert straight in value.unmet_requirements
    assert straight not in value.matched_scaling


def test_mime_values_existing_held_card_effects_without_name_special_cases():
    evaluator = ContextualJokerSynergyEvaluator()

    plain = BalatroState()
    plain.deck = [BalatroCard("A", "Spades")]

    steel = BalatroState()
    steel.deck = [BalatroCard("A", "Spades", enhancement="Steel")]

    plain_value = evaluator.evaluate(MimeJoker(), plain)
    steel_value = evaluator.evaluate(MimeJoker(), steel)

    assert HELD_EFFECT not in plain_value.amplified_features
    assert HELD_EFFECT in steel_value.amplified_features
    assert steel_value.interaction_gain > plain_value.interaction_gain


def test_mime_and_baron_match_in_either_candidate_direction():
    evaluator = ContextualJokerSynergyEvaluator()

    baron_build = BalatroState()
    baron_build.deck = _deck_with_kings(4)
    baron_build.jokers = [BaronJoker()]
    mime_candidate = evaluator.evaluate(MimeJoker(), baron_build)

    mime_build = BalatroState()
    mime_build.deck = _deck_with_kings(4)
    mime_build.jokers = [MimeJoker()]
    baron_candidate = evaluator.evaluate(BaronJoker(), mime_build)

    assert HELD_EFFECT in mime_candidate.amplified_features
    assert HELD_EFFECT in baron_candidate.reverse_amplified_features
    assert mime_candidate.interaction_gain > 0.0
    assert baron_candidate.interaction_gain > 0.0


def test_mime_does_not_treat_blackboard_as_retriggerable_held_card_effect():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()
    state.jokers = [BlackboardJoker()]

    value = evaluator.evaluate(MimeJoker(), state)

    assert HELD_EFFECT not in value.amplified_features
    assert not any(
        "Blackboard" in contribution.detail and contribution.feature == HELD_EFFECT
        for contribution in value.contributions
    )


def test_blueprint_copy_is_discovered_from_real_pair_behavior():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()
    state.deck = _deck_with_kings(4)
    state.jokers = [BaronJoker()]

    value = evaluator.evaluate(BlueprintJoker(), state)

    copy_interactions = [
        interaction
        for interaction in value.pair_interactions
        if interaction.kind == "COPY"
    ]
    assert any(
        interaction.actor_role == "candidate"
        and interaction.target_role == "existing"
        and interaction.target == "BaronJoker"
        for interaction in copy_interactions
    )
    assert any(
        contribution.kind == "PAIR_COPY" and contribution.amount > 0.0
        for contribution in value.contributions
    )
    assert value.interaction_gain > 0.0


def test_pair_probe_detects_generic_joker_presence_dependence():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()
    state.jokers = [AbstractJoker()]

    value = evaluator.evaluate(BaronJoker(), state)

    assert any(
        interaction.kind == "CONTEXT_DELTA"
        and interaction.actor_role == "existing"
        and interaction.actor == "AbstractJoker"
        and "score:mult" in interaction.features
        for interaction in value.pair_interactions
    )
    assert any(
        contribution.kind == "PAIR_CONTEXT_DELTA"
        and contribution.amount > 0.0
        for contribution in value.contributions
    )


def test_non_joker_candidate_stays_zero_and_conservative():
    evaluator = ContextualJokerSynergyEvaluator()
    state = BalatroState()

    value = evaluator.evaluate(object(), state)

    assert value.descriptor.kind == "UNKNOWN"
    assert value.intrinsic_gain == 0.0
    assert value.interaction_gain == 0.0
    assert value.total_gain == 0.0
    assert value.contributions == ()
