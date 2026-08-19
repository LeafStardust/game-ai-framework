from games.balatro.blind_skip_policy import BuildAwareBlindSkipPolicy
from games.balatro.live.external.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.hand_action_policy import HandActionThresholds
from games.balatro.live.planet_policy import LivePlanetPolicy
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.playbook_shop_policy import (
    PlaybookBuildAwareShopArbiter,
    PlaybookShopUtilityScale,
    PlaybookVoucherAwareBalatroShopPolicy,
)
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.shop_policy import DefaultShopItemValueEstimator
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy


def _runner():
    return PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )


def test_production_runner_shares_one_intent_tracker_across_b3_consumers():
    runner = _runner()

    assert isinstance(runner.shop_policy, VoucherAwareBalatroShopPolicy)
    assert isinstance(runner.shop_policy, PlaybookVoucherAwareBalatroShopPolicy)
    assert isinstance(runner.shop_arbiter, PlaybookBuildAwareShopArbiter)
    assert isinstance(runner.shop_arbiter.utility_scale, PlaybookShopUtilityScale)
    assert runner.shop_arbiter.shop_policy is runner.shop_policy
    assert runner.shop_reroll_policy.shop_policy is runner.shop_policy

    estimator = runner.shop_policy.item_value_estimator
    assert isinstance(estimator, DefaultShopItemValueEstimator)
    assert isinstance(estimator, BuildAwareShopItemValueEstimator)
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

    planet_policy = runner.consumable_timing_policy.planet_policy
    assert isinstance(planet_policy, LivePlanetPolicy)
    assert planet_policy.intent_tracker is runner.playstyle_intent_tracker
    assert planet_policy.profiler is runner.playstyle_profiler

    # Joker choices in packs reuse the exact D2/D14 evaluator instead of creating
    # an independent pack-local Joker intent lifecycle.
    assert isinstance(runner.pack_policy, PlaybookBalatroPackPolicy)
    assert runner.pack_policy.item_estimator is estimator

    pack_playstyle = runner.pack_policy.playstyle_evaluator
    assert isinstance(pack_playstyle, PackPlaystyleEvaluator)
    assert pack_playstyle.intent_tracker is runner.playstyle_intent_tracker
    assert pack_playstyle.profiler is runner.playstyle_profiler

    blind_skip = runner.blind_skip_policy
    assert isinstance(blind_skip, BuildAwareBlindSkipPolicy)
    assert blind_skip.intent_tracker is runner.playstyle_intent_tracker
    assert blind_skip.profiler is runner.playstyle_profiler

    build_log = runner.build_intent_log_tracker
    assert build_log.intent_tracker is runner.playstyle_intent_tracker
    assert build_log.profiler is runner.playstyle_profiler


def test_fresh_runner_gets_fresh_run_scoped_intent_and_logging_trackers():
    first = _runner()
    second = _runner()

    assert first.playstyle_intent_tracker is not second.playstyle_intent_tracker
    assert first.build_intent_log_tracker is not second.build_intent_log_tracker
    assert first.blind_skip_policy.intent_tracker is not second.blind_skip_policy.intent_tracker