from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy


def test_autonomous_shop_uses_voucher_aware_d3_policy():
    runner = LiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )

    assert isinstance(runner.shop_policy, VoucherAwareBalatroShopPolicy)
    assert runner.shop_reroll_policy.shop_policy is runner.shop_policy
    assert runner.shop_arbiter.shop_policy is runner.shop_policy
