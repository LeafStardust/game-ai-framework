from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.boss_hand_constraint_policy import _mouth_discard_only_decision
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _plan(name: str, *, score: float = 0.0):
    return LiveBlindPlan(
        action=BalatroAction(name, cards=[]),
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.0,
            expected_score=score,
            expected_hands_remaining=1.0,
            expected_discards_remaining=3.0,
        ),
        horizon=1,
        exact=False,
        candidate_count=1,
    )


def test_mouth_discard_only_legality_returns_recovery_instead_of_crashing(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    state = SimpleNamespace(
        boss_name="The Mouth",
        boss_blind_only_hand="Two Pair",
        blind=SimpleNamespace(requirement=4000),
        score=3996,
        hands_remaining=1,
        discards_remaining=4,
        hand=[],
        jokers=[],
        consumables=[],
        consumable_slots=2,
    )
    weaker = _plan(DISCARD_CARDS, score=100.0)
    stronger = _plan(DISCARD_CARDS, score=200.0)

    monkeypatch.setattr(policy, "_within_type_key", lambda plan: (plan.value.expected_score,))
    monkeypatch.setattr(policy.evaluator, "evaluate", lambda _state, action: 2.0 if action is stronger.action else 1.0)
    monkeypatch.setattr(policy.build_evaluator, "prepare", lambda _state: None)
    monkeypatch.setattr(policy.build_evaluator, "reset_cache", lambda: None)

    decision = _mouth_discard_only_decision(policy, state, (weaker, stronger))

    assert decision is not None
    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == DISCARD_CARDS
    assert decision.selected_plan is stronger
    assert decision.best_discard is stronger


def test_mouth_discard_only_helper_does_not_claim_non_mouth_state():
    policy = StrategyAwareLiveHandActionPolicy()
    state = SimpleNamespace(
        boss_name="The Psychic",
        boss_blind_only_hand=None,
    )

    assert _mouth_discard_only_decision(policy, state, (_plan(DISCARD_CARDS),)) is None
