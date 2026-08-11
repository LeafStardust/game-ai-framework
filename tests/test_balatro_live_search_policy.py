from types import SimpleNamespace

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.external import live_search_policy


class _Evaluator:
    def __init__(self, expected_hand_score):
        self.expected_hand_score = expected_hand_score

    def project_play(self, state, action):
        return SimpleNamespace(expected_hand_score=self.expected_hand_score)


class _Planner:
    def __init__(self, plan, expected_hand_score):
        self._plan = plan
        self.evaluator = _Evaluator(expected_hand_score)
        self.nodes_evaluated = 1

    def plan(self, state):
        return self._plan


def _state(card):
    return SimpleNamespace(
        hand=[card],
        score=0,
        hands_remaining=4,
        discards_remaining=4,
        blind=SimpleNamespace(requirement=300),
    )


def _args(*, min_pace_ratio=1.0):
    return SimpleNamespace(
        allow_pace_fallback=True,
        min_pace_ratio=min_pace_ratio,
        min_clear_probability=0.75,
        max_search_nodes=10000,
        exact_limit=1000,
        child_exact_limit=None,
    )


def _plan(card, expected_total=75.0):
    return LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=[card]),
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=expected_total / 300.0,
            expected_score=expected_total,
            expected_hands_remaining=3.0,
            expected_discards_remaining=4.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=1,
    )


def test_pace_fallback_accepts_remaining_blind_per_remaining_hand(monkeypatch):
    card = BalatroCard("A", "Spades")
    plan = _plan(card)
    monkeypatch.setattr(
        live_search_policy,
        "_planner",
        lambda config, args: _Planner(plan, expected_hand_score=75.0),
    )

    decision = live_search_policy._pace_fallback(_state(card), _args())

    assert decision is not None
    assert decision.mode == "pace-play"
    assert decision.result is not None
    assert decision.result.plan.action.cards == [card]


def test_pace_fallback_rejects_play_below_configured_pace(monkeypatch):
    card = BalatroCard("A", "Spades")
    plan = _plan(card)
    monkeypatch.setattr(
        live_search_policy,
        "_planner",
        lambda config, args: _Planner(plan, expected_hand_score=75.0),
    )

    decision = live_search_policy._pace_fallback(
        _state(card),
        _args(min_pace_ratio=1.1),
    )

    assert decision is not None
    assert decision.mode == "none"
