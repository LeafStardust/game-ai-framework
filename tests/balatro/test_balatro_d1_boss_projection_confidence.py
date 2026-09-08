from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    HandActionDecision,
    HandActionThresholds,
)
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


_BOSS_RATIONALE = (
    "boss projection exactness is treated as model-dependent until independently confirmed"
)


def _plan(*, exact=True):
    return LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=["play"]),
        value=LiveBlindPlanValue(
            clear_probability=1.0,
            expected_progress=1.0,
            expected_score=100.0,
            expected_hands_remaining=1.0,
            expected_discards_remaining=0.0,
        ),
        horizon=2,
        exact=exact,
        candidate_count=1,
    )


def _decision(plan, *, confidence=1.0):
    return HandActionDecision(
        mode=CLEAR_PATH,
        action=plan.action,
        selected_plan=plan,
        best_play=plan,
        best_discard=None,
        thresholds=HandActionThresholds(),
        pace_target=100.0,
        best_play_immediate_score=100.0,
        best_play_pace_ratio=1.0,
        selected_immediate_score=100.0,
        selected_pace_ratio=1.0,
        selected_fallback_value=None,
        clear_path_candidates=1,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=False,
        confidence=confidence,
        rationale=("parent decision",),
        candidate_count=1,
        plans=(plan,),
    )


def _isolated_policy(monkeypatch, captured):
    policy = object.__new__(StrategyAwareLiveHandActionPolicy)
    monkeypatch.setattr(
        policy,
        "_enforce_safe_pace_scope",
        lambda state, plans, decision, **kwargs: decision,
    )
    monkeypatch.setattr(
        policy,
        "_refine_strategy_safe_pace",
        lambda state, plans, decision: decision,
    )
    monkeypatch.setattr(policy, "_vagabond_generation_active", lambda state: False)
    monkeypatch.setattr(policy, "_strategy_fit", lambda state, action: (0.0, ()))

    def parent_decide(self, state, plans, **kwargs):
        del self, state
        supplied = tuple(plans)
        captured["plans"] = supplied
        captured["kwargs"] = kwargs
        return _decision(supplied[0])

    monkeypatch.setattr(BuildAwareLiveHandActionPolicy, "decide", parent_decide)
    return policy


def _boss_state():
    return SimpleNamespace(
        boss_name="The Hook",
        blind_type="BOSS",
        hands_remaining=2,
        discards_remaining=0,
    )


def test_unconfirmed_boss_projection_is_downgraded_inside_strategy_policy(monkeypatch):
    captured = {}
    policy = _isolated_policy(monkeypatch, captured)
    plan = _plan(exact=True)

    decision = policy.decide(_boss_state(), [plan])

    assert plan.exact is True
    assert captured["plans"][0].exact is False
    assert decision.confidence == 0.95
    assert decision.rationale[0] == _BOSS_RATIONALE


def test_confirmed_boss_projection_preserves_exactness_and_confidence(monkeypatch):
    captured = {}
    policy = _isolated_policy(monkeypatch, captured)
    plan = _plan(exact=True)

    decision = policy.decide(
        _boss_state(),
        [plan],
        confirmed_clear_path=plan,
    )

    assert captured["plans"][0].exact is True
    assert decision.confidence == 1.0
    assert _BOSS_RATIONALE not in decision.rationale
