from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    dead = BalatroCard("5", "Hearts", live_id=1, debuffed=True)
    live = BalatroCard("5", "Clubs", live_id=2)
    state.hand = [dead, live]
    state.deck = []
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 2
    state.blind = Blind(BlindType.BOSS, 10000)
    state.jokers = []
    return state, dead, live


def test_d1_recovery_prefers_discarding_debuffed_card_when_structure_is_equal():
    state, dead, live = _state()
    evaluator = LiveHandDecisionEvaluator()
    context = evaluator._context(state)

    discard_dead = evaluator._discard_value(
        state,
        BalatroAction(DISCARD_CARDS, cards=[dead]),
        context,
    )
    discard_live = evaluator._discard_value(
        state,
        BalatroAction(DISCARD_CARDS, cards=[live]),
        context,
    )

    assert discard_dead > discard_live
    assert discard_dead - discard_live == 16.0


def test_d1_recovery_has_no_debuff_bias_when_hand_has_no_debuffed_cards():
    state, dead, live = _state()
    dead.debuffed = False
    evaluator = LiveHandDecisionEvaluator()
    context = evaluator._context(state)

    left = evaluator._discard_value(
        state,
        BalatroAction(DISCARD_CARDS, cards=[dead]),
        context,
    )
    right = evaluator._discard_value(
        state,
        BalatroAction(DISCARD_CARDS, cards=[live]),
        context,
    )

    assert left == right
