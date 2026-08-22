from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import LiveHandActionPolicy
from games.balatro.state import BalatroState


class _Evaluator:
    def project_play(self, state, action):
        cards = tuple(action.cards)
        score = 100.0 if len(cards) == 1 and cards[0].rank == "6" else 150.0
        return SimpleNamespace(expected_hand_score=score)

    def evaluate(self, state, action):
        return self.project_play(state, action).expected_hand_score


class _LowSixEvaluator(_Evaluator):
    def project_play(self, state, action):
        cards = tuple(action.cards)
        score = 60.0 if len(cards) == 1 and cards[0].rank == "6" else 150.0
        return SimpleNamespace(expected_hand_score=score)


def _plan(action, expected_score):
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.0,
            expected_score=float(expected_score),
            expected_hands_remaining=3.0,
            expected_discards_remaining=3.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )


def _state():
    state = BalatroState()
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.blind = SimpleNamespace(requirement=400)
    state.round_hand_play_counts = {key: 0 for key in state.round_hand_play_counts}
    state.jokers = [SixthSenseJoker()]
    state.consumables = []
    state.consumable_slots = 2
    return state


def _played_ranks(action):
    return tuple(str(card.rank) for card in getattr(action, "cards", ()) or ())


def test_first_hand_sixth_sense_is_used_when_single_six_still_meets_pace():
    state = _state()
    six_action = BalatroAction(PLAY_CARDS, cards=[BalatroCard("6", "Hearts")])
    normal_action = BalatroAction(
        PLAY_CARDS,
        cards=[BalatroCard("A", "Spades"), BalatroCard("A", "Hearts")],
    )
    decision = LiveHandActionPolicy(evaluator=_Evaluator()).decide(
        state,
        [_plan(normal_action, 150), _plan(six_action, 100)],
    )

    assert decision.action.name == PLAY_CARDS
    assert _played_ranks(decision.action) == ("6",)
    assert any("Sixth Sense opportunity" in note for note in decision.rationale)


def test_sixth_sense_does_not_sabotage_pace_to_trigger():
    state = _state()
    six_action = BalatroAction(PLAY_CARDS, cards=[BalatroCard("6", "Hearts")])
    normal_action = BalatroAction(
        PLAY_CARDS,
        cards=[BalatroCard("A", "Spades"), BalatroCard("A", "Hearts")],
    )
    decision = LiveHandActionPolicy(evaluator=_LowSixEvaluator()).decide(
        state,
        [_plan(normal_action, 150), _plan(six_action, 60)],
    )

    assert decision.action.name == PLAY_CARDS
    assert _played_ranks(decision.action) == ("A", "A")


def test_sixth_sense_does_not_destroy_six_when_consumable_slots_are_full():
    state = _state()
    state.consumables = [object(), object()]
    six_action = BalatroAction(PLAY_CARDS, cards=[BalatroCard("6", "Hearts")])
    normal_action = BalatroAction(
        PLAY_CARDS,
        cards=[BalatroCard("A", "Spades"), BalatroCard("A", "Hearts")],
    )
    decision = LiveHandActionPolicy(evaluator=_Evaluator()).decide(
        state,
        [_plan(normal_action, 150), _plan(six_action, 100)],
    )

    assert decision.action.name == PLAY_CARDS
    assert _played_ranks(decision.action) == ("A", "A")
