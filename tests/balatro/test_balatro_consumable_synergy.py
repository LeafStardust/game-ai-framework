from games.balatro.build import (
    ContextualConsumableSynergyEvaluator,
    HELD_EFFECT,
    enhancement_feature,
    hand_feature,
    rank_feature,
)
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot, Magician, Strength


def test_chariot_is_more_valuable_when_mime_can_amplify_created_steel():
    evaluator = ContextualConsumableSynergyEvaluator()

    neutral = BalatroState()
    neutral.hand = [BalatroCard("Q", "Hearts")]
    neutral_eval = evaluator.evaluate(Chariot(), neutral)

    mime_build = BalatroState()
    mime_build.hand = [BalatroCard("Q", "Hearts")]
    mime_build.jokers = [MimeJoker()]
    mime_eval = evaluator.evaluate(Chariot(), mime_build)

    assert mime_eval.total_gain > neutral_eval.total_gain
    assert HELD_EFFECT in mime_eval.prospective_features
    assert any(
        path.consumer == "MimeJoker"
        and path.derived_feature == HELD_EFFECT
        and path.relationship == "AMPLIFIED_BY_BUILD"
        for path in mime_eval.paths
    )


def test_mime_prefers_steel_transform_over_unrelated_lucky_transform():
    evaluator = ContextualConsumableSynergyEvaluator()
    state = BalatroState()
    state.hand = [BalatroCard("Q", "Hearts")]
    state.jokers = [MimeJoker()]

    ranked = evaluator.rank([Magician(), Chariot()], state)

    assert ranked[0].candidate == "The Chariot"
    assert ranked[0].total_gain > ranked[1].total_gain
    assert any(path.derived_feature == HELD_EFFECT for path in ranked[0].paths)
    assert not any(path.derived_feature == HELD_EFFECT for path in ranked[1].paths)


def test_strength_exposes_prospective_held_king_path_for_baron():
    evaluator = ContextualConsumableSynergyEvaluator()
    state = BalatroState()
    state.hand = [BalatroCard("Q", "Clubs")]
    state.jokers = [BaronJoker()]

    evaluation = evaluator.evaluate(Strength(), state)

    king = rank_feature("K")
    held_king = rank_feature("K", held=True)
    assert king in evaluation.descriptor.transforms
    assert held_king in evaluation.prospective_features
    assert any(
        path.consumer == "BaronJoker"
        and path.source_feature == king
        and path.derived_feature == held_king
        for path in evaluation.paths
    )


def test_mercury_gains_build_path_value_from_pair_engine():
    evaluator = ContextualConsumableSynergyEvaluator()
    mercury = create_planet("MERCURY")

    neutral = BalatroState()
    neutral_eval = evaluator.evaluate(mercury, neutral)

    pair_build = BalatroState()
    pair_build.jokers = [TheDuoJoker()]
    pair_eval = evaluator.evaluate(mercury, pair_build)

    pair_feature = hand_feature("PAIR")
    assert pair_eval.total_gain > neutral_eval.total_gain
    assert any(
        path.consumer == "TheDuoJoker"
        and path.derived_feature == pair_feature
        for path in pair_eval.paths
    )


def test_unrelated_transform_keeps_only_conservative_setup_value():
    evaluator = ContextualConsumableSynergyEvaluator()
    state = BalatroState()
    state.hand = [BalatroCard("Q", "Hearts")]

    evaluation = evaluator.evaluate(Magician(), state)

    lucky = enhancement_feature("Lucky")
    assert lucky in evaluation.descriptor.transforms
    assert evaluation.paths == ()
    assert any(
        contribution.kind == "PROSPECTIVE_TRANSFORM"
        and contribution.feature == lucky
        for contribution in evaluation.contributions
    )
