from __future__ import annotations

"""Read-only live monitor wrapper with a visible decision-thinking timer.

The supervisor already publishes a timestamped ``THINKING`` telemetry record before
calling the decision stack.  Derive elapsed wall time from that timestamp inside the
monitor process so timing observability cannot add work to gameplay policy.
"""

from datetime import datetime, timezone
from typing import Any

from . import balatro_agent_monitor as base_monitor


_BASE_BUILD_DASHBOARD = base_monitor.build_dashboard


def _thinking_elapsed_seconds(
    telemetry: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> float | None:
    telemetry = telemetry or {}
    if str(telemetry.get("activity") or "").upper() != "THINKING":
        return None
    raw = telemetry.get("updated_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        started = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return max(0.0, (current - started).total_seconds())


def _decision_timer_line(telemetry: dict[str, Any] | None) -> str:
    elapsed = _thinking_elapsed_seconds(telemetry)
    if elapsed is None:
        return "Decision timer   : -"
    return f"Decision timer   : {elapsed:.1f}s (THINKING)"


def build_dashboard_with_timer(*args, **kwargs) -> str:
    telemetry = kwargs.get("telemetry")
    rendered = _BASE_BUILD_DASHBOARD(*args, **kwargs)
    timer_line = _decision_timer_line(telemetry)
    activity = str((telemetry or {}).get("activity") or "WAITING")
    marker = f"Agent activity   : {activity}"
    if marker in rendered:
        return rendered.replace(marker, marker + "\n" + timer_line, 1)
    return timer_line + "\n" + rendered


def main() -> int:
    # Patch only the monitor process. The autonomous supervisor/policy process never
    # imports this wrapper, so the ticking display cannot alter decision latency.
    base_monitor.build_dashboard = build_dashboard_with_timer
    return base_monitor.main()


if __name__ == "__main__":
    raise SystemExit(main())
