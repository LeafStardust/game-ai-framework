from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.reserved_parking import ReservedParkingJoker
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(played, held, jokers, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(played) + list(held)
    state.deck = []
    state.money = money
    state.jokers = list(jokers)
    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        played,
    )
    return state, transition


def _probability_by_score(distribution):
    result = {}
    for outcome in distribution.outcomes:
        result[outcome.score] = result.get(outcome.score, 0.0) + outcome.probability
    return result


def test_reserved_parking_money_reaches_bull_same_hand():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts")
    state, transition = _project(
        [ace],
        [king],
        [ReservedParkingJoker(), BullJoker()],
    )

    probabilities = _probability_by_score(transition.distribution)
    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert abs(probabilities[16] - 0.5) < 1e-12
    assert abs(probabilities[18] - 0.5) < 1e-12
    assert set(transition.distribution.random_sources) == {"Reserved Parking x1"}
    assert state.money == 0

    money_by_score = {
        outcome.score: outcome.state_after_scoring.money
        for outcome in transition.distribution.outcomes
    }
    assert money_by_score[16] == 0
    assert money_by_score[18] == 1


def test_reserved_parking_oops_makes_half_chance_guaranteed():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts")
    _, transition = _project(
        [ace],
        [king],
        [ReservedParkingJoker(), OopsAll6sJoker(), BullJoker()],
    )

    assert len(transition.distribution.outcomes) == 1
    outcome = transition.distribution.outcomes[0]
    assert outcome.score == 18
    assert outcome.probability == 1.0
    assert outcome.state_after_scoring.money == 1


def test_reserved_parking_uses_pareidolia_face_semantics():
    ace = BalatroCard("A", "Spades")
    held_two = BalatroCard("2", "Clubs")
    _, transition = _project(
        [ace],
        [held_two],
        [PareidoliaJoker(), ReservedParkingJoker(), BullJoker()],
    )

    probabilities = _probability_by_score(transition.distribution)
    assert abs(probabilities[16] - 0.5) < 1e-12
    assert abs(probabilities[18] - 0.5) < 1e-12


def test_reserved_parking_skips_debuffed_held_faces():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts")
    king.debuffed = True
    _, transition = _project(
        [ace],
        [king],
        [ReservedParkingJoker(), BullJoker()],
    )

    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.outcomes[0].state_after_scoring.money == 0
    assert "Reserved Parking x1" not in transition.distribution.random_sources


def test_reserved_parking_red_seal_and_mime_retrigger_each_roll():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts", seal="Red")
    _, transition = _project(
        [ace],
        [king],
        [ReservedParkingJoker(), MimeJoker(), BullJoker()],
    )

    probabilities = _probability_by_score(transition.distribution)
    assert set(probabilities) == {16, 18, 20, 22}
    assert abs(probabilities[16] - 0.125) < 1e-12
    assert abs(probabilities[18] - 0.375) < 1e-12
    assert abs(probabilities[20] - 0.375) < 1e-12
    assert abs(probabilities[22] - 0.125) < 1e-12
    assert "Reserved Parking x3" in transition.distribution.random_sources


def test_blueprint_targeting_reserved_parking_stays_fail_closed():
    ace = BalatroCard("A", "Spades")
    king = BalatroCard("K", "Hearts")
    _, transition = _project(
        [ace],
        [king],
        [BlueprintJoker(), ReservedParkingJoker()],
    )

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers
