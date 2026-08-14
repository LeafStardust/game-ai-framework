from games.balatro.live.external.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.shop_policy import DefaultShopItemValueEstimator


def _runner():
    return PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )


def test_production_runner_shares_one_intent_tracker_between_d1_and_d2():
    runner = _runner()

    estimator = runner.shop_policy.item_value_estimator
    assert isinstance(estimator, DefaultShopItemValueEstimator)
    assert (
        estimator.joker_build_value.intent_tracker
        is runner.playstyle_intent_tracker
    )
    assert estimator.joker_build_value.profiler is runner.playstyle_profiler

    hand_policy = runner._hand_policy(HandActionThresholds())
    assert (
        hand_policy.playstyle_evaluator.intent_tracker
        is runner.playstyle_intent_tracker
    )
    assert hand_policy.playstyle_evaluator.profiler is runner.playstyle_profiler


def test_fresh_runner_gets_fresh_run_scoped_intent_tracker():
    first = _runner()
    second = _runner()

    assert first.playstyle_intent_tracker is not second.playstyle_intent_tracker
