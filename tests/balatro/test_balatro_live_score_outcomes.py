from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.state import BalatroState


def _state(cards, *, score=0, target=600):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = cards
    state.score = score
    state.blind = Blind(BlindType.BOSS, target)
    state.jokers = []
    return state


def test_deterministic_pair_has_single_exact_outcome():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert distribution.deterministic is True
    assert distribution.minimum == 60
    assert distribution.expected == 60.0
    assert distribution.maximum == 60
    assert distribution.outcomes[0].probability == 1.0


def test_one_lucky_pair_card_has_floor_expected_and_upside_distribution():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert distribution.minimum == 60
    assert distribution.maximum == 660
    assert abs(distribution.expected - 180.0) < 1e-9
    assert [(outcome.score, round(outcome.probability, 10)) for outcome in distribution.outcomes] == [
        (60, 0.8),
        (660, 0.2),
    ]
    assert abs(distribution.probability_at_least(500) - 0.2) < 1e-9


def test_red_seal_retriggers_rank_chips_and_lucky_mult_independently():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky", seal="Red"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair base 10 + first 10 + retriggered first 10 + second 10 = 40 chips.
    # Lucky triggers twice: 0, 1 or 2 +20 Mult successes.
    assert distribution.minimum == 80
    assert distribution.maximum == 1680
    assert abs(distribution.expected - 400.0) < 1e-9
    assert [(outcome.score, round(outcome.probability, 10)) for outcome in distribution.outcomes] == [
        (80, 0.64),
        (880, 0.32),
        (1680, 0.04),
    ]


def test_live_projection_exposes_probabilistic_clear_without_claiming_guarantee():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky", live_id=0),
        BalatroCard("10", "Diamonds", live_id=1),
    ]
    state = _state(cards, score=100, target=600)
    action = BalatroAction(PLAY_CARDS, cards=cards)

    projection = LiveHandDecisionEvaluator().project_play(state, action)

    assert projection.hand == PokerHand.PAIR
    assert projection.hand_score == 60
    assert projection.expected_hand_score == 180.0
    assert projection.maximum_hand_score == 660
    assert projection.projected_total == 160
    assert projection.maximum_projected_total == 760
    assert projection.clears_blind is False
    assert projection.possible_clear is True
    assert abs(projection.clear_probability - 0.2) < 1e-9
