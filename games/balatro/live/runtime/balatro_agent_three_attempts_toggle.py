from __future__ import annotations

import sys

from . import balatro_agent_toggle as base_toggle


THREE_ATTEMPT_SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_three_attempts_entry"
)


def _strip_selector(argv: list[str]) -> None:
    """Consume the batch-only --three selector forwarded through ``%*``."""

    argv[:] = [arg for arg in argv if arg.lower() != "--three"]


def main() -> int:
    """Run the shared toggle with a scoped three-attempt supervisor override."""
    previous = base_toggle.SUPERVISOR_MODULE
    base_toggle.SUPERVISOR_MODULE = THREE_ATTEMPT_SUPERVISOR_MODULE
    try:
        return base_toggle.main()
    finally:
        # Importing this launcher in a long-lived process (notably the full test
        # suite) must not silently redirect the canonical one-run toggle.
        base_toggle.SUPERVISOR_MODULE = previous


if __name__ == "__main__":
    _strip_selector(sys.argv)
    raise SystemExit(main())
