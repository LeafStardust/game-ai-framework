from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bloodstone import BloodstoneJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(cards, jokers, *, hand=PokerHand.HIGH_CARD):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    return VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def _outcomes(transition):
    return [
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ]


def test_bloodstone_is_admitted_to_live_joker_projection():
    assert LiveJokerScoreProjector.supports(BloodstoneJoker()) is True


def test_one_scored_heart_has_exact_bloodstone_distribution():
    ace = BalatroCard("A", "Hearts")
    transition = _project([ace], [BloodstoneJoker()])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert _outcomes(transition) == [
        (16, 0.5),
        (24, 0.5),
    ]
    assert transition.distribution.random_sources == ("Bloodstone x1",)


def test_non_scoring_heart_kicker_does_not_roll_bloodstone():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("2", "Hearts"),
    ]
    transition = _project(
        cards,
        [BloodstoneJoker()],
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 60
    assert transition.distribution.random_sources == ()


def test_bloodstone_xmult_resolves_in_on_scored_joker_order():
    ten = BalatroCard("10", "Hearts")

    bloodstone_first = _project(
        [ten],
        [BloodstoneJoker(), LustyJoker()],
    )
    lusty_first = _project(
        [ten],
        [LustyJoker(), BloodstoneJoker()],
    )

    assert _outcomes(bloodstone_first) == [
        (60, 0.5),
        (67, 0.5),
    ]
    assert _outcomes(lusty_first) == [
        (60, 0.5),
        (90, 0.5),
    ]


def test_smeared_joker_makes_diamonds_eligible_for_bloodstone():
    cards = [
        BalatroCard("10", "Hearts"),
        BalatroCard("10", "Diamonds"),
    ]
    transition = _project(
        cards,
        [SmearedJoker(), BloodstoneJoker()],
        hand=PokerHand.PAIR,
    )

    assert transition.joker_projection_complete is True
    assert _outcomes(transition) == [
        (60, 0.25),
        (90, 0.5),
        (135, 0.25),
    ]
    assert transition.distribution.random_sources == ("Bloodstone x2",)


def test_red_seal_retriggers_bloodstone_probability_check():
    ace = BalatroCard("A", "Hearts", seal="Red")
    transition = _project([ace], [BloodstoneJoker()])

    assert _outcomes(transition) == [
        (27, 0.25),
        (40, 0.5),
        (60, 0.25),
    ]
    assert transition.distribution.random_sources == ("Bloodstone x2",)


def test_lucky_and_bloodstone_branches_preserve_card_activation_order():
    ace = BalatroCard("A", "Hearts", enhancement="Lucky")
    transition = _project([ace], [BloodstoneJoker()])

    assert transition.joker_projection_complete is True
    assert _outcomes(transition) == [
        (16, 0.4),
        (24, 0.4),
        (336, 0.1),
        (504, 0.1),
    ]
    assert transition.distribution.random_sources == (
        "Lucky mult x1",
        "Bloodstone x1",
    )
