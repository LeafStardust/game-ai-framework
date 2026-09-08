from __future__ import annotations

import sys

from . import balatro_agent_toggle as base_toggle


ONE_ATTEMPT_SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_one_attempt_entry"
)


def _strip_selector(argv: list[str]) -> None:
    """Consume the batch-only --one selector if it is forwarded directly."""

    argv[:] = [arg for arg in argv if arg.lower() != "--one"]


def main() -> int:
    """Run the shared toggle with a scoped one-attempt supervisor override."""
    previous = base_toggle.SUPERVISOR_MODULE
    base_toggle.SUPERVISOR_MODULE = ONE_ATTEMPT_SUPERVISOR_MODULE
    try:
        return base_toggle.main()
    finally:
        base_toggle.SUPERVISOR_MODULE = previous


if __name__ == "__main__":
    _strip_selector(sys.argv)
    raise SystemExit(main())
