from __future__ import annotations

import os
import sys
from pathlib import Path

from . import balatro_agent_toggle as base_toggle
from .agent_control import BalatroAgentControl
from .balatro_agent_attempts_entry import ATTEMPTS_ENV


ATTEMPT_SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_attempts_entry"
)


def _consume_attempt(argv: list[str]) -> int:
    for index, arg in enumerate(list(argv)):
        if arg.lower() != "--attempt":
            continue
        if index + 1 >= len(argv):
            raise ValueError("--attempt requires a positive integer")
        raw = argv[index + 1]
        try:
            attempts = int(raw)
        except ValueError as error:
            raise ValueError("--attempt requires a positive integer") from error
        if attempts <= 0:
            raise ValueError("--attempt requires a positive integer")
        del argv[index : index + 2]
        return attempts
    raise ValueError("--attempt is required")


def _control_from_argv(argv: list[str]) -> BalatroAgentControl:
    for index, arg in enumerate(argv):
        if arg == "--control-dir" and index + 1 < len(argv):
            return BalatroAgentControl(Path(argv[index + 1]))
    return BalatroAgentControl(None)


def main() -> int:
    attempts = _consume_attempt(sys.argv)
    control = _control_from_argv(sys.argv)
    was_running = control.running_pid() is not None
    previous_module = base_toggle.SUPERVISOR_MODULE
    previous_attempts = os.environ.get(ATTEMPTS_ENV)
    base_toggle.SUPERVISOR_MODULE = ATTEMPT_SUPERVISOR_MODULE
    os.environ[ATTEMPTS_ENV] = str(attempts)
    try:
        result = base_toggle.main()
        if result != 0:
            return result
        if not was_running:
            base_toggle.wait_for_startup_outcome(control)
        return 0
    except RuntimeError as error:
        print("Balatro Agent bounded attempt -> FAIL")
        print(f"Reason -> {error}")
        return 2
    finally:
        base_toggle.SUPERVISOR_MODULE = previous_module
        if previous_attempts is None:
            os.environ.pop(ATTEMPTS_ENV, None)
        else:
            os.environ[ATTEMPTS_ENV] = previous_attempts


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"Balatro Agent attempts -> FAIL: {error}")
        raise SystemExit(2)
