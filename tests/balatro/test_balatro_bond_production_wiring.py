from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.live.runtime.balatro_agent_supervisor_entry import (
    _diagnostic_runner_factory,
)
from games.balatro.live.runtime.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.runtime.strategy_autonomous_runner import (
    StrategyAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.verdant_leaf import VerdantLeafSalePolicy
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.unlock_campaign import UnlockCampaignPolicy


def test_production_supervisor_uses_canonical_bond_runner():
    assert (
        _diagnostic_runner_factory.__globals__["StrategyAwareLiveMemoryInjectedSingleStepRunner"]
        is StrategyAwareLiveMemoryInjectedSingleStepRunner
    )
    assert issubclass(
        StrategyAwareLiveMemoryInjectedSingleStepRunner,
        PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
    )


def test_canonical_runner_has_no_historical_strategy_tracker_dependency():
    globals_ = StrategyAwareLiveMemoryInjectedSingleStepRunner.__init__.__globals__
    assert "TreeAwareStateAwareBalatroStrategyTracker" not in globals_
    assert "BalatroStrategyTracker" not in globals_
    assert globals_["JokerBuildValueEvaluator"] is JokerBuildValueEvaluator


def test_canonical_runner_retains_mechanical_support_policies():
    globals_ = StrategyAwareLiveMemoryInjectedSingleStepRunner.__init__.__globals__
    assert globals_["JokerOrderPolicy"] is JokerOrderPolicy
    assert globals_["VerdantLeafSalePolicy"] is VerdantLeafSalePolicy
    assert globals_["UnlockCampaignPolicy"] is UnlockCampaignPolicy
