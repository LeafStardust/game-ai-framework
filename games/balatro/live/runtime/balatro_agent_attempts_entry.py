from __future__ import annotations

import os

from . import balatro_agent_supervisor_entry as base_entry
from .balatro_agent_bounded_supervisor import BoundedBalatroAgentSupervisor


ATTEMPTS_ENV = "BALATRO_AGENT_MAX_ATTEMPTS"


def _configured_attempts() -> int:
    raw = os.environ.get(ATTEMPTS_ENV, "")
    try:
        attempts = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{ATTEMPTS_ENV} must be a positive integer") from error
    if attempts <= 0:
        raise ValueError(f"{ATTEMPTS_ENV} must be a positive integer")
    return attempts


class ConfiguredAttemptBalatroAgentSupervisor(BoundedBalatroAgentSupervisor):
    """Run ordinary production policy for the launcher-requested attempt count."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("max_attempts", _configured_attempts())
        super().__init__(*args, **kwargs)


base_entry.BalatroAgentSupervisor = ConfiguredAttemptBalatroAgentSupervisor


if __name__ == "__main__":
    raise SystemExit(base_entry.main())
