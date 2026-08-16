from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.business_card import BusinessCardJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(hand, cards, jokers, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.money = money
    state.jokers = list(jokers)
    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )
    return state, transition


def _probability_by_money(distribution):
    result = {}
    for outcome in distribution.outcomes:
        money = outcome.state_after_scoring.money
        result[money] = result.get(money, 0.0) + outcome.probability
    return result


def _probability_by_score(distribution):
    result = {}
    for outcome in distribution.outcomes:
        result[outcome.score] = result.get(outcome.score, 0.0) + outcome.probability
    return result


def test_business_card_branches_scored_face_card_money_without_mutating_parent():
    king = BalatroCard("K", "Spades")
    state, transition = _project(
        PokerHand.HIGH_CARD,
        [king],
        [BusinessCardJoker()],
    )

    probabilities = _probability_by_money(transition.distribution)

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 15
    assert transition.distribution.maximum == 15
    assert abs(probabilities[0] - 0.5) < 1e-12
    assert abs(probabilities[2] - 0.5) < 1e-12
    assert transition.distribution.random_sources == ("Business Card x1",)
    assert state.money == 0


def test_business_card_ignores_non_scoring_face_kicker():
    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Diamonds"),
    ]
    _, transition = _project(
        PokerHand.PAIR,
        cards,
        [BusinessCardJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 64
    assert transition.distribution.outcomes[0].state_after_scoring.money == 0


def test_business_card_respects_pareidolia_face_semantics():
    ace = BalatroCard("A", "Spades")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [ace],
        [PareidoliaJoker(), BusinessCardJoker()],
    )

    probabilities = _probability_by_money(transition.distribution)
    assert abs(probabilities[0] - 0.5) < 1e-12
    assert abs(probabilities[2] - 0.5) < 1e-12


def test_business_card_retriggers_roll_again():
    king = BalatroCard("K", "Spades", seal="Red")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [king],
        [BusinessCardJoker()],
    )

    probabilities = _probability_by_money(transition.distribution)
    assert transition.distribution.minimum == 25
    assert transition.distribution.maximum == 25
    assert abs(probabilities[0] - 0.25) < 1e-12
    assert abs(probabilities[2] - 0.5) < 1e-12
    assert abs(probabilities[4] - 0.25) < 1e-12
    assert transition.distribution.random_sources == ("Business Card x2",)


def test_oops_all_6s_guarantees_business_card_money():
    king = BalatroCard("K", "Spades")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [king],
        [OopsAll6sJoker(), BusinessCardJoker()],
    )

    assert transition.joker_projection_complete is True
    assert len(transition.distribution.outcomes) == 1
    outcome = transition.distribution.outcomes[0]
    assert outcome.probability == 1.0
    assert outcome.score == 15
    assert outcome.state_after_scoring.money == 2


def test_business_card_money_reaches_bull_in_same_hand():
    king = BalatroCard("K", "Spades")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [king],
        [BusinessCardJoker(), BullJoker()],
    )

    probabilities = _probability_by_score(transition.distribution)
    assert abs(probabilities[15] - 0.5) < 1e-12
    assert abs(probabilities[19] - 0.5) < 1e-12

    money_by_score = {
        outcome.score: outcome.state_after_scoring.money
        for outcome in transition.distribution.outcomes
    }
    assert money_by_score == {15: 0, 19: 2}


def test_business_card_composes_with_existing_lucky_replay():
    king = BalatroCard("K", "Spades", enhancement="Lucky")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [king],
        [BusinessCardJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert {outcome.score for outcome in transition.distribution.outcomes} == {15, 315}
    assert {
        outcome.state_after_scoring.money
        for outcome in transition.distribution.outcomes
    } == {0, 2}
    assert abs(sum(
        outcome.probability
        for outcome in transition.distribution.outcomes
    ) - 1.0) < 1e-12
    assert "Lucky mult x1" in transition.distribution.random_sources
    assert "Business Card x1" in transition.distribution.random_sources
