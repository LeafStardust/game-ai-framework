from games.balatro.live.runtime.balatro_agent_supervisor_entry import (
    _is_recovered_stale_replan,
)
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepGuardError,
)
from games.balatro.live.runtime.v09g_diagnostic_report import (
    _is_recovered_stale_replan as report_is_recovered_stale_replan,
    render,
)


def _row(error_type, error, *, stage="execution_failure"):
    return {
        "schema": "balatro-diagnostic-v1",
        "session_id": "session-test",
        "sequence": 1,
        "stage": stage,
        "data": {
            "error_type": error_type,
            "error": error,
            "phase": "SELECTING_HAND",
            "action": "PLAY_CARDS",
        },
    }


def test_runtime_suppresses_only_expected_stale_replan_guard():
    stale = AutonomousStepGuardError(
        "live state changed after autonomous planning; decide again from the new checkpoint"
    )
    other_guard = AutonomousStepGuardError("achievement gate unavailable")

    assert _is_recovered_stale_replan(stale) is True
    assert _is_recovered_stale_replan(other_guard) is False
    assert _is_recovered_stale_replan(RuntimeError(str(stale))) is False


def test_report_classifies_existing_stale_execution_failure_as_recovered():
    row = _row(
        "AutonomousStepGuardError",
        "live state changed after autonomous planning; decide again from the new checkpoint",
    )

    assert report_is_recovered_stale_replan(row) is True
    output = render("session-test", [row])
    assert "Recovered stale replans         : 1" in output
    assert "Actionable failure/block events : 0" in output
    assert "PASS — all diagnostics are recovered stale-state replans" in output


def test_report_keeps_other_execution_failures_actionable():
    row = _row("InjectedBridgeError", "bridge timed out")

    assert report_is_recovered_stale_replan(row) is False
    output = render("session-test", [row])
    assert "Recovered stale replans         : 0" in output
    assert "Actionable failure/block events : 1" in output
    assert "REVIEW — genuine diagnostic events remain" in output
