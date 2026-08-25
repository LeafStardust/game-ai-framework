from __future__ import annotations

import sys

from . import balatro_agent_toggle as base_toggle


FIVE_ATTEMPT_SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_five_attempts_entry"
)


def _strip_selector(argv: list[str]) -> None:
    """Consume the batch-only --five selector if it was forwarded by cmd.exe."""
    argv[:] = [arg for arg in argv if arg.lower() != "--five"]


def main() -> int:
    """Run the shared toggle with a scoped five-attempt supervisor override."""
    previous = base_toggle.SUPERVISOR_MODULE
    base_toggle.SUPERVISOR_MODULE = FIVE_ATTEMPT_SUPERVISOR_MODULE
    try:
        return base_toggle.main()
    finally:
        base_toggle.SUPERVISOR_MODULE = previous


if __name__ == "__main__":
    # Mutate the actual sys.argv list. ``sys.argv[1:]`` would create a copy and
    # leave argparse seeing the original ``--five`` selector.
    _strip_selector(sys.argv)
    raise SystemExit(main())
