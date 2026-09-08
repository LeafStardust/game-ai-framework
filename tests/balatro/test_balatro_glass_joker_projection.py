import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(card, *jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [card]
    state.deck = []
    state.owned_deck = [card]
    state.jokers = list(jokers)
    return state


def _glass_x_mult(state):
    joker = next(
        joker
        for joker in state.jokers
        if type(joker).__name__ == "GlassJoker"
    )
    return joker.x_mult


def test_glass_joker_hydrates_owned_x_mult_from_public_live_state():
    joker = LiveJokerFactory().create(
        {
            "center": "j_glass",
            "label": "Glass Joker",
            "public_state": {"x_mult": 3.25},
        }
    )

    assert isinstance(joker, GlassJoker)
    assert joker.x_mult == 3.25


def test_glass_joker_scores_from_its_owned_x_mult_not_global_break_history():
    ace = BalatroCard("A", "Spades", live_id=1)
    joker = GlassJoker()
    joker.x_mult = 1.75
    state = _state(ace, joker)
    state.glass_cards_destroyed = 99

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 28
    assert _glass_x_mult(transition.state_after_scoring) == 1.75


def test_glass_break_grows_joker_only_on_broken_branch_for_future_hands():
    card = BalatroCard("K", "Hearts", enhancement="Glass", live_id=7)
    joker = GlassJoker()
    joker.x_mult = 2.0
    state = _state(card, joker)

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.random_sources == ("Glass break x1",)
    assert len(transition.distribution.outcomes) == 2

    outcomes = sorted(
        transition.distribution.outcomes,
        key=lambda outcome: len(outcome.state_after_scoring.owned_deck),
    )
    broken, survived = outcomes

    # The Glass Joker was X2 while this hand scored, so both RNG branches score
    # the same 60 chips. Growth happens after scoring and affects future hands.
    assert broken.score == 60
    assert survived.score == 60
    assert broken.probability == pytest.approx(0.25)
    assert survived.probability == pytest.approx(0.75)

    assert len(broken.state_after_scoring.owned_deck) == 0
    assert _glass_x_mult(broken.state_after_scoring) == pytest.approx(2.75)
    assert len(survived.state_after_scoring.owned_deck) == 1
    assert _glass_x_mult(survived.state_after_scoring) == pytest.approx(2.0)

    assert len(state.owned_deck) == 1
    assert joker.x_mult == 2.0


def test_oops_all_6s_doubles_glass_break_probability_and_growth_branch():
    card = BalatroCard("K", "Hearts", enhancement="Glass", live_id=7)
    glass = GlassJoker()
    glass.x_mult = 1.5
    state = _state(card, glass, OopsAll6sJoker())

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    outcomes = transition.distribution.outcomes
    assert len(outcomes) == 2
    assert sorted(outcome.probability for outcome in outcomes) == [0.5, 0.5]

    broken = next(
        outcome
        for outcome in outcomes
        if len(outcome.state_after_scoring.owned_deck) == 0
    )
    assert _glass_x_mult(broken.state_after_scoring) == pytest.approx(2.25)


def test_two_glass_breaks_add_point_seven_five_each_to_branch_state():
    first = BalatroCard("K", "Hearts", enhancement="Glass", live_id=1)
    second = BalatroCard("K", "Spades", enhancement="Glass", live_id=2)
    glass = GlassJoker()
    glass.x_mult = 1.0
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [first, second]
    state.deck = []
    state.owned_deck = [first, second]
    state.jokers = [glass]

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        [first, second],
    )

    by_owned_count = {
        len(outcome.state_after_scoring.owned_deck): outcome
        for outcome in transition.distribution.outcomes
    }
    assert _glass_x_mult(by_owned_count[2].state_after_scoring) == 1.0
    assert _glass_x_mult(by_owned_count[0].state_after_scoring) == pytest.approx(2.5)

    one_break = [
        outcome
        for outcome in transition.distribution.outcomes
        if len(outcome.state_after_scoring.owned_deck) == 1
    ]
    assert one_break
    assert all(
        _glass_x_mult(outcome.state_after_scoring) == pytest.approx(1.75)
        for outcome in one_break
    )


def test_blueprint_can_copy_glass_joker_current_independent_x_mult():
    ace = BalatroCard("A", "Spades", live_id=1)
    glass = GlassJoker()
    glass.x_mult = 2.0
    state = _state(ace, BlueprintJoker(), glass)

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 64
