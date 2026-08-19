from games.balatro.live.external.live_memory_achievement_guard import (
    achievement_gate_state,
)


def test_unset_achievement_gate_is_not_disabled():
    state, disabled = achievement_gate_state("UNSET")
    assert state == "UNSET"
    assert disabled is False


def test_enabled_achievement_gate_is_not_disabled():
    state, disabled = achievement_gate_state("ENABLED")
    assert state == "ENABLED"
    assert disabled is False


def test_disabled_achievement_gate_is_disabled():
    state, disabled = achievement_gate_state("DISABLED")
    assert state == "DISABLED"
    assert disabled is True


def test_missing_achievement_gate_fails_closed():
    state, disabled = achievement_gate_state(None)
    assert state == "MISSING"
    assert disabled is None


def test_unavailable_achievement_gate_fails_closed():
    state, disabled = achievement_gate_state("G_UNAVAILABLE")
    assert state == "G_UNAVAILABLE"
    assert disabled is None


def test_unexpected_achievement_gate_fails_closed():
    state, disabled = achievement_gate_state("UNEXPECTED:number")
    assert state == "UNEXPECTED:number"
    assert disabled is None
