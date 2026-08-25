from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.joker_policy import BUY, JokerAcquisitionPolicy
from games.balatro.jokers.square_joker import SquareJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy
from games.balatro.state import BalatroState


def test_first_affordable_direct_scoring_joker_beats_empty_engine_hold():
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 1
    state.money = 7
    state.joker_slots = 5
    state.jokers = []

    candidate = SquareJoker()
    candidate.cost = 4
    candidate.discovered = True

    decision = JokerAcquisitionPolicy().decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.economics.money_after == 3
    assert any("first-engine bootstrap" in note for note in decision.rationale)


def test_paint_brush_cannot_preempt_first_scoring_foothold():
    state = SimpleNamespace(
        ante=1,
        jokers=[],
        hand_levels={"PAIR": 1},
    )
    profile = SimpleNamespace(
        ante=1,
        joker_names=(),
        hand_levels=(("PAIR", 1),),
    )

    allowed, notes = VoucherAcquisitionPolicy._early_survival_gate(
        state,
        profile,
        "Paint Brush",
        price=10,
        money_after=4,
    )

    assert allowed is False
    assert any("first-engine hold" in note for note in notes)


def test_underpace_recovery_values_multi_card_redraw_as_one_discard_resource():
    evaluator = object.__new__(LiveHandDecisionEvaluator)
    evaluator._cached_state_id = None
    evaluator._cached_context = None
    evaluator.scorer = SimpleNamespace(is_card_debuffed=lambda card: False)
    evaluator._has_guaranteed_clearing_play = lambda state: False
    evaluator._retained_structure_value = lambda cards: 0.0

    cards = [object() for _ in range(8)]
    state = SimpleNamespace(
        hand=cards,
        discards_remaining=4,
        hands_remaining=4,
    )
    context = SimpleNamespace(
        best_play_score=25.0,
        required_per_hand=100.0,
        best_play_hand=None,
    )

    single = BalatroAction(DISCARD_CARDS, cards=[cards[0]])
    batch = BalatroAction(DISCARD_CARDS, cards=cards[:4])
    single_value = evaluator._discard_value(state, single, context)
    batch_value = evaluator._discard_value(state, batch, context)

    # Canonical count reward alone is only +12 from one to four cards. The live
    # competence correction must add a material fixed-resource redraw advantage.
    assert batch_value - single_value > 40.0


def test_live_planner_discard_beam_uses_canonical_d1_value():
    class RecordingEvaluator:
        def __init__(self):
            self.calls = []

        def evaluate(self, state, action):
            self.calls.append((state, action))
            return 100.0 * len(action.cards)

    evaluator = RecordingEvaluator()
    planner = object.__new__(LiveBlindClearPlanner)
    planner.evaluator = evaluator
    cards = [object() for _ in range(4)]
    state = SimpleNamespace(hand=cards)
    single = BalatroAction(DISCARD_CARDS, cards=cards[:1])
    batch = BalatroAction(DISCARD_CARDS, cards=cards[:4])

    single_priority = planner._discard_priority(state, single)
    batch_priority = planner._discard_priority(state, batch)

    assert single_priority == (100.0, 1)
    assert batch_priority == (400.0, 4)
    assert evaluator.calls == [(state, single), (state, batch)]
    assert batch_priority > single_priority
