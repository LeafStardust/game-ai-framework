from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


def _play_action(card):
    return BalatroAction(PLAY_CARDS, cards=(card,))


def test_native_outer_d1_evaluation_cache_reuses_same_state_action():
    class _CountingEvaluator(LiveHandDecisionEvaluator):
        def __init__(self):
            super().__init__()
            self.play_value_calls = 0

        def _context(self, state):
            del state
            return SimpleNamespace()

        def _play_value(self, state, action, context):
            del state, action, context
            self.play_value_calls += 1
            return 7.0

    evaluator = _CountingEvaluator()
    card = BalatroCard("A", "Spades")
    action = _play_action(card)
    first_state = SimpleNamespace()

    assert evaluator.evaluate(first_state, action) == 7.0
    assert evaluator.evaluate(first_state, action) == 7.0
    assert evaluator.play_value_calls == 1

    assert evaluator.evaluate(SimpleNamespace(), action) == 7.0
    assert evaluator.play_value_calls == 2


def test_native_outer_d1_projection_cache_reuses_transition():
    evaluator = LiveHandDecisionEvaluator()
    card = BalatroCard("A", "Spades")
    action = _play_action(card)
    state = SimpleNamespace(
        score=0,
        blind=SimpleNamespace(requirement=100),
    )
    calls = {"count": 0}

    distribution = SimpleNamespace(
        minimum=10,
        expected=10.0,
        maximum=10,
        outcomes=(),
        random_sources=(),
        probability_at_least=lambda remaining: 0.0,
    )

    def project_transition(*args, **kwargs):
        del args, kwargs
        calls["count"] += 1
        return SimpleNamespace(
            distribution=distribution,
            state_after_scoring=None,
            joker_projection_complete=True,
            unsupported_jokers=(),
        )

    evaluator.score_outcomes.project_transition = project_transition

    first = evaluator.project_play(state, action)
    second = evaluator.project_play(state, action)

    assert first is second
    assert calls["count"] == 1


def test_native_outer_d1_guaranteed_clear_scan_is_cached():
    evaluator = LiveHandDecisionEvaluator()
    card = BalatroCard("A", "Spades")
    action = _play_action(card)
    state = SimpleNamespace(
        score=0,
        blind=SimpleNamespace(requirement=5),
    )
    calls = {"count": 0}

    evaluator.action_generator = SimpleNamespace(
        generate_play_actions=lambda current_state: (action,),
    )
    evaluator._hand_for_cards = lambda current_state, cards: PokerHand.HIGH_CARD

    def project(*args, **kwargs):
        del args, kwargs
        calls["count"] += 1
        return SimpleNamespace(minimum=10)

    evaluator.score_outcomes.project = project

    assert evaluator._has_guaranteed_clearing_play(state) is True
    assert evaluator._has_guaranteed_clearing_play(state) is True
    assert calls["count"] == 1
