from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlan,
    LiveBlindPlanValue,
    _ActionEstimate,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _plan(*, action_name: str, score: float, exact: bool, clear: float = 0.0):
    action = BalatroAction(action_name, cards=[])
    value = LiveBlindPlanValue(
        clear_probability=clear,
        expected_progress=clear,
        expected_score=score,
        expected_hands_remaining=3.0,
        expected_discards_remaining=2.0,
    )
    return LiveBlindPlan(
        action=action,
        value=value,
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def test_sampled_wider_recovery_can_beat_exact_singleton_quality():
    exact_singleton = _plan(
        action_name=DISCARD_CARDS,
        score=900.0,
        exact=True,
    )
    sampled_wider = _plan(
        action_name=DISCARD_CARDS,
        score=1400.0,
        exact=False,
    )

    policy = StrategyAwareLiveHandActionPolicy()

    assert policy._within_type_key(sampled_wider) > policy._within_type_key(exact_singleton)

    exact_estimate = _ActionEstimate(
        exact_singleton.action,
        exact_singleton.value,
        exact_singleton.exact,
    )
    sampled_estimate = _ActionEstimate(
        sampled_wider.action,
        sampled_wider.value,
        sampled_wider.exact,
    )
    assert LiveBlindClearPlanner._estimate_key(sampled_estimate) > LiveBlindClearPlanner._estimate_key(exact_estimate)


def test_exact_guaranteed_clear_still_outranks_non_guaranteed_recovery():
    guaranteed = _plan(
        action_name=PLAY_CARDS,
        score=1000.0,
        exact=True,
        clear=1.0,
    )
    sampled_recovery = _plan(
        action_name=DISCARD_CARDS,
        score=10000.0,
        exact=False,
        clear=0.99,
    )

    guaranteed_estimate = _ActionEstimate(
        guaranteed.action,
        guaranteed.value,
        guaranteed.exact,
    )
    recovery_estimate = _ActionEstimate(
        sampled_recovery.action,
        sampled_recovery.value,
        sampled_recovery.exact,
    )

    assert LiveBlindClearPlanner._estimate_key(guaranteed_estimate) > LiveBlindClearPlanner._estimate_key(recovery_estimate)
