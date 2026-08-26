from datetime import datetime, timezone

import games.balatro.live.runtime.balatro_agent_monitor_timed as timed_monitor


def test_thinking_timer_uses_telemetry_timestamp():
    telemetry = {
        "activity": "THINKING",
        "updated_at": "2026-08-27T00:00:00+00:00",
    }

    elapsed = timed_monitor._thinking_elapsed_seconds(
        telemetry,
        now=datetime(2026, 8, 27, 0, 0, 12, 500000, tzinfo=timezone.utc),
    )

    assert elapsed == 12.5


def test_timer_is_inactive_outside_thinking():
    telemetry = {
        "activity": "DECIDED",
        "updated_at": "2026-08-27T00:00:00+00:00",
    }

    assert timed_monitor._thinking_elapsed_seconds(telemetry) is None


def test_dashboard_injects_visible_thinking_timer(monkeypatch):
    monkeypatch.setattr(
        timed_monitor,
        "_BASE_BUILD_DASHBOARD",
        lambda *args, **kwargs: "Agent state      : ON\nAgent activity   : THINKING\nSupervisor      : RUNNING",
    )
    monkeypatch.setattr(timed_monitor, "_decision_timer_line", lambda telemetry: "Decision timer   : 7.5s (THINKING)")

    rendered = timed_monitor.build_dashboard_with_timer(
        {},
        supervisor_pid=1,
        balatro_running=True,
        rows=[],
        telemetry={"activity": "THINKING"},
    )

    assert "Agent activity   : THINKING\nDecision timer   : 7.5s (THINKING)" in rendered
