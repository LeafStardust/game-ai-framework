from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _discard_plan(*, score: float, exact: bool, clear: float = 0.0):
    action = BalatroAction(DISCARD_CARDS, cards=[])
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
    exact_singleton = _discard_plan(score=900.0, exact=True)
    sampled_wider = _discard_plan(score=1400.0, exact=False)

    policy = StrategyAwareLiveHandActionPolicy()

    assert policy._within_type_key(sampled_wider) > policy._within_type_key(exact_singleton)


def test_exactness_breaks_only_equal_discard_recovery_quality_ties():
    exact = _discard_plan(score=1400.0, exact=True)
    sampled = _discard_plan(score=1400.0, exact=False)

    policy = StrategyAwareLiveHandActionPolicy()

    assert policy._within_type_key(exact) > policy._within_type_key(sampled)
