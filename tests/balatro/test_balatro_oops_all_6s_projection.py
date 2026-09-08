from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bloodstone import BloodstoneJoker
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0, owned_deck=None):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    state.money = money
    state.owned_deck = None if owned_deck is None else list(owned_deck)
    return state


def _project(card, jokers, *, money=0, owned_deck=None):
    state = _state(
        [card],
        jokers,
        money=money,
        owned_deck=owned_deck,
    )
    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )


def _scores(transition):
    return [
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ]


def test_oops_all_6s_is_admitted_as_blind_probability_modifier():
    joker = OopsAll6sJoker()
    assert LiveJokerScoreProjector.supports(joker) is True

    ace = BalatroCard("A", "Spades")
    transition = _project(ace, [joker])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16


def test_one_oops_doubles_lucky_mult_probability():
    lucky = BalatroCard("A", "Spades", enhancement="Lucky")
    transition = _project(lucky, [OopsAll6sJoker()])

    assert transition.joker_projection_complete is True
    assert _scores(transition) == [
        (16, 0.6),
        (336, 0.4),
    ]
    assert transition.distribution.random_sources == ("Lucky mult x1",)


def test_two_oops_quadruple_lucky_mult_probability():
    lucky = BalatroCard("A", "Spades", enhancement="Lucky")
    transition = _project(
        lucky,
        [OopsAll6sJoker(), OopsAll6sJoker()],
    )

    assert transition.joker_projection_complete is True
    assert _scores(transition) == [
        (16, 0.2),
        (336, 0.8),
    ]


def test_oops_makes_bloodstone_guaranteed():
    heart = BalatroCard("A", "Hearts")
    transition = _project(
        heart,
        [BloodstoneJoker(), OopsAll6sJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    assert _scores(transition) == [(24, 1.0)]
    assert transition.distribution.random_sources == ("Bloodstone x1",)


def test_oops_doubles_glass_break_probability_and_preserves_state_branch():
    glass = BalatroCard("A", "Spades", enhancement="Glass", live_id=51)
    owned = BalatroCard("A", "Spades", enhancement="Glass", live_id=51)
    transition = _project(
        glass,
        [OopsAll6sJoker()],
        owned_deck=[owned],
    )

    assert transition.joker_projection_complete is True
    assert _scores(transition) == [
        (32, 0.5),
        (32, 0.5),
    ]
    assert transition.distribution.random_sources == ("Glass break x1",)
    assert sorted(
        len(outcome.state_after_scoring.owned_deck)
        for outcome in transition.distribution.outcomes
    ) == [0, 1]


def test_oops_doubles_lucky_money_probability_before_bootstraps():
    lucky = BalatroCard("A", "Spades", enhancement="Lucky")
    transition = _project(
        lucky,
        [OopsAll6sJoker(), BootstrapsJoker()],
        money=0,
    )

    assert transition.joker_projection_complete is True
    money_branches = [
        outcome
        for outcome in transition.distribution.outcomes
        if outcome.state_after_scoring.money == 20
    ]
    assert abs(sum(outcome.probability for outcome in money_branches) - (2.0 / 15.0)) < 1e-9
