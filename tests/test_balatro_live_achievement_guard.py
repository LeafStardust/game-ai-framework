from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.external.live_memory_achievement_guard import (
    achievement_gate_state,
)


def test_missing_achievement_gate_is_not_disabled():
    state, disabled = achievement_gate_state(None)
    assert state == "UNSET"
    assert disabled is False


def test_false_achievement_gate_is_not_disabled():
    state, disabled = achievement_gate_state(
        LuaValue("boolean", False, 0)
    )
    assert state == "ENABLED"
    assert disabled is False


def test_true_achievement_gate_is_disabled():
    state, disabled = achievement_gate_state(
        LuaValue("boolean", True, 0)
    )
    assert state == "DISABLED"
    assert disabled is True


def test_unexpected_achievement_gate_fails_closed():
    state, disabled = achievement_gate_state(
        LuaValue("integer", 1, 0)
    )
    assert state == "UNEXPECTED:integer"
    assert disabled is None
