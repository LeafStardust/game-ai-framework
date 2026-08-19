from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.mr_bones import MrBonesJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _state(*, target: int, hands: int = 1, mr_bones: bool = True):
    cards = [
        BalatroCard("K", "Spades"),
        BalatroCard("K", "Hearts"),
    ]
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = cards
    state.deck = []
    state.score = 0
    state.hands_remaining = hands
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, target)
    state.jokers = [MrBonesJoker()] if mr_bones else []
    return state, cards


def test_mr_bones_is_admitted_without_changing_raw_hand_score():
    state, cards = _state(target=240)

    projection = LiveHandDecisionEvaluator().project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=cards),
    )

    assert projection.hand_score == 60
    assert projection.clear_probability == 0.0
    assert projection.joker_projection_complete is True
    assert projection.unsupported_jokers == ()


def test_mr_bones_rescues_final_hand_at_exact_quarter_threshold():
    state, _ = _state(target=240)

    plan = LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        horizon=1,
    ).plan(state)

    assert len(plan.action.cards) == 2
    assert plan.value.expected_score == 60.0
    assert plan.value.clear_probability == 1.0
    assert plan.value.expected_progress == 1.0
    assert plan.exact is True


def test_mr_bones_does_not_rescue_below_quarter_threshold():
    state, _ = _state(target=241)

    plan = LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        horizon=1,
    ).plan(state)

    assert plan.value.expected_score == 60.0
    assert plan.value.clear_probability == 0.0
    assert plan.value.expected_progress < 1.0
    assert plan.exact is True


def test_mr_bones_does_not_rescue_before_hands_are_exhausted():
    state, _ = _state(target=240, hands=2)

    plan = LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        horizon=1,
    ).plan(state)

    assert plan.value.expected_score == 60.0
    assert plan.value.clear_probability == 0.0
    assert plan.value.expected_progress == 0.25
    assert plan.exact is True


def test_without_mr_bones_final_quarter_score_is_still_a_loss():
    state, _ = _state(target=240, mr_bones=False)

    plan = LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        horizon=1,
    ).plan(state)

    assert plan.value.expected_score == 60.0
    assert plan.value.clear_probability == 0.0
    assert plan.value.expected_progress == 0.25
    assert plan.exact is True
