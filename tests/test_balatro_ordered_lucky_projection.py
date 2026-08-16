from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(cards, *, jokers=None, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.money = money
    state.jokers = list(jokers or [])
    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )


def _probability_by_score(distribution):
    result = {}
    for outcome in distribution.outcomes:
        result[outcome.score] = result.get(outcome.score, 0.0) + outcome.probability
    return result


def test_lucky_mult_resolves_before_later_glass_xmult():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Hearts", enhancement="Glass"),
    ]

    distribution = _project(cards).distribution
    probabilities = _probability_by_score(distribution)

    assert distribution.minimum == 120
    assert distribution.maximum == 1320
    assert abs(probabilities[120] - 0.8) < 1e-12
    assert abs(probabilities[1320] - 0.2) < 1e-12


def test_lucky_after_glass_keeps_later_additive_order():
    cards = [
        BalatroCard("10", "Spades", enhancement="Glass"),
        BalatroCard("10", "Hearts", enhancement="Lucky"),
    ]

    distribution = _project(cards).distribution
    probabilities = _probability_by_score(distribution)

    assert distribution.minimum == 120
    assert distribution.maximum == 720
    assert abs(probabilities[120] - 0.8) < 1e-12
    assert abs(probabilities[720] - 0.2) < 1e-12


def test_lucky_money_reaches_bull_before_joker_row_scoring():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Hearts"),
    ]

    transition = _project(cards, jokers=[BullJoker()])
    probabilities = _probability_by_score(transition.distribution)

    assert abs(probabilities[60] - (0.8 * 14 / 15)) < 1e-12
    assert abs(probabilities[140] - (0.8 / 15)) < 1e-12
    assert abs(probabilities[660] - (0.2 * 14 / 15)) < 1e-12
    assert abs(probabilities[1540] - (0.2 / 15)) < 1e-12

    money_scores = {
        outcome.score
        for outcome in transition.distribution.outcomes
        if outcome.state_after_scoring.money == 20
    }
    assert money_scores == {140, 1540}


def test_lucky_money_reaches_bootstraps_before_later_cavendish():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Hearts"),
    ]

    transition = _project(
        cards,
        jokers=[BootstrapsJoker(), CavendishJoker()],
    )
    probabilities = _probability_by_score(transition.distribution)

    assert set(probabilities) == {180, 900, 1980, 2700}
    assert abs(probabilities[180] - (0.8 * 14 / 15)) < 1e-12
    assert abs(probabilities[900] - (0.8 / 15)) < 1e-12
    assert abs(probabilities[1980] - (0.2 * 14 / 15)) < 1e-12
    assert abs(probabilities[2700] - (0.2 / 15)) < 1e-12


def test_lucky_cat_growth_precedes_same_hand_joker_activation():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Hearts"),
    ]

    transition = _project(cards, jokers=[LuckyCatJoker()])
    probabilities = _probability_by_score(transition.distribution)

    assert transition.distribution.minimum == 60
    assert transition.distribution.maximum == 825
    assert abs(probabilities[60] - (0.8 * 14 / 15)) < 1e-12
    assert abs(probabilities[75] - (0.8 / 15)) < 1e-12
    assert abs(probabilities[825] - 0.2) < 1e-12

    grown = [
        outcome
        for outcome in transition.distribution.outcomes
        if outcome.score != 60
    ]
    assert grown
    for outcome in grown:
        lucky_cat = next(
            joker
            for joker in outcome.state_after_scoring.jokers
            if type(joker).__name__ == "LuckyCatJoker"
        )
        assert lucky_cat.x_mult == 1.25


def test_simple_lucky_distribution_stays_compact_without_state_sensitive_joker():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Hearts"),
    ]

    distribution = _project(cards).distribution
    probabilities = _probability_by_score(distribution)

    assert len(distribution.outcomes) == 2
    assert abs(probabilities[60] - 0.8) < 1e-12
    assert abs(probabilities[660] - 0.2) < 1e-12
