from __future__ import annotations

import sys

from . import balatro_agent_toggle as base_toggle


base_toggle.SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_three_attempts_entry"
)
base_toggle.MONITOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_monitor_targets"
)


def _strip_selector(argv: list[str]) -> None:
    """Consume the batch-only --three selector forwarded through ``%*``."""

    argv[:] = [arg for arg in argv if arg.lower() != "--three"]


if __name__ == "__main__":
    _strip_selector(sys.argv)
    raise SystemExit(base_toggle.main())
