from __future__ import annotations

from . import balatro_agent_toggle as base_toggle


base_toggle.SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_five_attempts_entry"
)
base_toggle.MONITOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_monitor_targets"
)


if __name__ == "__main__":
    raise SystemExit(base_toggle.main())
