from games.balatro.build import HELD_EFFECT, ContextualJokerSynergyEvaluator
from games.balatro.card import BalatroCard
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.mime import MimeJoker
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
