from games.balatro.live.runtime.balatro_agent_supervisor_entry import (
    _diagnostic_runner_factory,
)
from games.balatro.live.runtime.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.runtime.strategy_autonomous_runner import (
    StrategyAwareLiveMemoryInjectedSingleStepRunner,
    _strategy_modifiers_for_state,
)
from games.balatro.state import BalatroState


def test_production_supervisor_entry_uses_strategy_aware_runner():
    assert (
        _diagnostic_runner_factory.__globals__["StrategyAwareLiveMemoryInjectedSingleStepRunner"]
        is StrategyAwareLiveMemoryInjectedSingleStepRunner
    )
    assert issubclass(
        StrategyAwareLiveMemoryInjectedSingleStepRunner,
        PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
    )


def test_production_strategy_runner_resolves_red_white_environment_modifiers():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"

    modifiers = _strategy_modifiers_for_state(state)

    assert modifiers["strategies"]["flush"]["effectiveness"] == 1.10
    assert modifiers["strategies"]["straight_flush"]["enabled"] is False
