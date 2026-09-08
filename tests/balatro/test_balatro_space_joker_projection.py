import games.balatro.jokers.space_joker as space_joker_module

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.space_joker import SpaceJoker
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(card, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [card]
    state.deck = []
    state.jokers = list(jokers)
    return state


def _project(card, jokers):
    return LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        _state(card, jokers),
        [card],
    )


def _level_branches(transition):
    return [
        (
            outcome.state_after_scoring.hand_levels["HIGH_CARD"],
            outcome.score,
            round(outcome.probability, 10),
        )
        for outcome in transition.distribution.outcomes
    ]


def test_space_joker_is_admitted_without_consuming_hidden_rng(monkeypatch):
    card = BalatroCard("A", "Spades")
    joker = SpaceJoker()
    state = _state(card, [joker])

    def fail_rng():
        raise AssertionError("projection consumed Space Joker RNG")

    monkeypatch.setattr(space_joker_module.random, "random", fail_rng)
    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    assert LiveJokerScoreProjector.supports(joker) is True
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.random_sources == ("Space Joker x1",)
    assert _level_branches(transition) == [
        (1, 16, 0.75),
        (2, 16, 0.25),
    ]
    assert state.hand_levels["HIGH_CARD"] == 1


def test_oops_all_6s_doubles_space_joker_level_probability():
    card = BalatroCard("A", "Spades")
    transition = _project(card, [SpaceJoker(), OopsAll6sJoker()])

    assert _level_branches(transition) == [
        (1, 16, 0.5),
        (2, 16, 0.5),
    ]


def test_multiple_space_jokers_stack_independent_level_rolls():
    card = BalatroCard("A", "Spades")
    transition = _project(card, [SpaceJoker(), SpaceJoker()])

    assert transition.distribution.random_sources == ("Space Joker x2",)
    assert _level_branches(transition) == [
        (1, 16, 0.5625),
        (2, 16, 0.375),
        (3, 16, 0.0625),
    ]


def test_live_hand_decision_exposes_space_joker_post_hand_states():
    card = BalatroCard("A", "Spades")
    state = _state(card, [SpaceJoker()])

    projection = LiveHandDecisionEvaluator().project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[card]),
    )

    assert projection.hand_score == 16
    assert projection.expected_hand_score == 16
    assert projection.random_sources == ("Space Joker x1",)
    assert [
        outcome.state_after_scoring.hand_levels["HIGH_CARD"]
        for outcome in projection.outcomes
    ] == [1, 2]


def test_blueprint_targeting_space_joker_remains_fail_closed():
    card = BalatroCard("A", "Spades")
    blueprint = BlueprintJoker()
    state = _state(card, [blueprint, SpaceJoker()])

    assert LiveJokerScoreProjector.supports(blueprint) is True
    assert LiveJokerScoreProjector.supports_in_state(blueprint, state) is False
