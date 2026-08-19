import pytest

from games.balatro.live.house_blind_planner import HouseBlindClearPlanner
from games.balatro.state import BalatroState


def _state(*, boss_name="The House"):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = boss_name
    state.hands_remaining = 4
    state.hand = [object()]
    return state


def test_house_planner_supports_only_the_house():
    assert HouseBlindClearPlanner.supports(_state()) is True
    assert HouseBlindClearPlanner.supports(_state(boss_name="The Head")) is False


def test_house_planner_rejects_other_bosses():
    planner = HouseBlindClearPlanner(horizon=1)

    with pytest.raises(ValueError, match="House planner requires The House"):
        planner.plan(_state(boss_name="The Head"))
