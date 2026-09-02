from __future__ import annotations

import inspect

import games.balatro  # noqa: F401 - install production policy stack
import games.balatro.planet_pack_fallback_policy as planet_policy
from games.balatro.state import BalatroState


def _state(*, levels=None, plays=None) -> BalatroState:
    state = BalatroState()
    state.jokers = []
    state.hand_levels = dict(levels or {})
    state.hand_play_counts = dict(plays or {})
    state.consumables = []
    return state


def test_h15_celestial_direction_has_no_strategy_controller_dependency():
    source = inspect.getsource(planet_policy)

    assert "evaluate_bond_composition" not in source
    assert "StrategyCommitment" not in source
    assert "strategy_plan" not in source.lower()
    assert "pinned_strategy" not in source.lower()
    assert "_plan_hand_goals" not in source


def test_h15_celestial_direction_requires_observed_hand_specialization():
    state = _state(
        levels={"PAIR": 4},
        plays={"PAIR": 0, "TWO_PAIR": 0},
    )

    assert not planet_policy._hand_direction(state)
    headroom, notes = planet_policy._celestial_headroom(state)
    assert headroom == 0
    assert any("no strong realized hand specialization" in note for note in notes)


def test_h15_observed_primary_hand_supplies_celestial_direction_and_headroom():
    state = _state(
        levels={"PAIR": 1, "TWO_PAIR": 1},
        plays={"PAIR": 8, "TWO_PAIR": 2},
    )

    assert planet_policy._hand_direction(state, "PAIR")
    assert not planet_policy._hand_direction(state, "TWO_PAIR")
    headroom, notes = planet_policy._celestial_headroom(state)
    assert headroom > 0
    assert any("PAIR" in note for note in notes)
