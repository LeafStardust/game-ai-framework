from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.state import BalatroState


def _state(money: int) -> BalatroState:
    state = BalatroState()
    state.money = money
    return state


def test_bull_literal_scoring_value_rises_with_current_cash():
    evaluator = JokerBuildValueEvaluator()

    broke = evaluator.evaluate(_state(0), BullJoker())
    rich = evaluator.evaluate(_state(100), BullJoker())

    assert rich.direct_scoring_gain > broke.direct_scoring_gain
    assert rich.direct_scoring_gain > 0.0


def test_bootstraps_literal_scoring_value_rises_with_current_cash():
    evaluator = JokerBuildValueEvaluator()

    broke = evaluator.evaluate(_state(0), BootstrapsJoker())
    rich = evaluator.evaluate(_state(100), BootstrapsJoker())

    assert rich.direct_scoring_gain > broke.direct_scoring_gain
    assert rich.direct_scoring_gain > 0.0
