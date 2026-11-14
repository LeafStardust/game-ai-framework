from types import SimpleNamespace

import pytest

from games.balatro.env.ppo_boss_safe_pace_sweep import (
    PPOBossSafePaceSweepError,
    _eligible_indices,
)


def _event(action, plans):
    return {
        "output": {"action": action},
        "completed_search_plans": plans,
    }


def test_safe_pace_sweep_selects_only_later_different_exact_plans():
    discard = {"name": "DISCARD_CARDS", "indices": [0]}
    play = {"name": "PLAY_CARDS", "indices": [1]}
    trace = {"terminal_decisions": (
        _event(discard, ({"exact": True, "action": play},)),
        _event(play, ({"exact": True, "action": play},)),
        _event(discard, ({"exact": False, "action": play},)),
        _event(discard, ({"exact": True, "action": play},)),
    )}
    assert _eligible_indices(trace) == (3,)


def test_safe_pace_sweep_fails_closed_without_eligible_later_plan():
    action = {"name": "PLAY_CARDS", "indices": [0]}
    trace = {"terminal_decisions": (_event(action, ()), _event(action, ()))}
    with pytest.raises(PPOBossSafePaceSweepError, match="no later"):
        _eligible_indices(trace)
