from __future__ import annotations

import sys

from . import balatro_agent_toggle as base_toggle


base_toggle.SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_five_attempts_entry"
)
base_toggle.MONITOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_monitor_targets"
)


def _strip_selector(argv: list[str]) -> None:
    """Consume the batch-only --five selector if it was forwarded by cmd.exe.

    Windows batch SHIFT updates %1/%2/etc. but leaves %* unchanged, so the wrapper
    can still forward the original selector. The five-attempt entrypoint treats it
    purely as a launcher selector and removes it before argparse sees the args.
    """
    argv[:] = [arg for arg in argv if arg.lower() != "--five"]


if __name__ == "__main__":
    _strip_selector(sys.argv[1:])
    raise SystemExit(base_toggle.main())
