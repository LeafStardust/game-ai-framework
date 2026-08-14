from games.balatro.live.external.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.shop_policy import DefaultShopItemValueEstimator


def _runner():
    return PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )


def test_production_runner_shares_one_intent_tracker_across_d1_d2_d9_and_logging():
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

    # Joker choices in packs reuse the exact D2 evaluator instead of creating an
    # independent pack-local Joker intent lifecycle.
    assert runner.pack_policy.item_estimator is estimator

    pack_playstyle = runner.pack_policy.playstyle_evaluator
    assert isinstance(pack_playstyle, PackPlaystyleEvaluator)
    assert pack_playstyle.intent_tracker is runner.playstyle_intent_tracker
    assert pack_playstyle.profiler is runner.playstyle_profiler

    build_log = runner.build_intent_log_tracker
    assert build_log.intent_tracker is runner.playstyle_intent_tracker
    assert build_log.profiler is runner.playstyle_profiler


def test_fresh_runner_gets_fresh_run_scoped_intent_and_logging_trackers():
    first = _runner()
    second = _runner()

    assert first.playstyle_intent_tracker is not second.playstyle_intent_tracker
    assert first.build_intent_log_tracker is not second.build_intent_log_tracker
