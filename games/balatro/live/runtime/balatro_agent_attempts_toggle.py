from __future__ import annotations

import os
import sys

from . import balatro_agent_toggle as base_toggle
from .balatro_agent_attempts_entry import ATTEMPTS_ENV


ATTEMPT_SUPERVISOR_MODULE = (
    "games.balatro.live.runtime.balatro_agent_attempts_entry"
)


def _consume_attempts(argv: list[str]) -> int:
    for index, arg in enumerate(list(argv)):
        if arg.lower() != "--attempts":
            continue
        if index + 1 >= len(argv):
            raise ValueError("--attempts requires a positive integer")
        raw = argv[index + 1]
        try:
            attempts = int(raw)
        except ValueError as error:
            raise ValueError("--attempts requires a positive integer") from error
        if attempts <= 0:
            raise ValueError("--attempts requires a positive integer")
        del argv[index : index + 2]
        return attempts
    raise ValueError("--attempts is required")


def main() -> int:
    attempts = _consume_attempts(sys.argv)
    previous_module = base_toggle.SUPERVISOR_MODULE
    previous_attempts = os.environ.get(ATTEMPTS_ENV)
    base_toggle.SUPERVISOR_MODULE = ATTEMPT_SUPERVISOR_MODULE
    os.environ[ATTEMPTS_ENV] = str(attempts)
    try:
        return base_toggle.main()
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
