from __future__ import annotations

from . import balatro_agent_supervisor_entry as base_entry
from .balatro_agent_bounded_supervisor import BoundedBalatroAgentSupervisor


class OneAttemptBalatroAgentSupervisor(BoundedBalatroAgentSupervisor):
    """Run ordinary production policy for exactly one attempt at most."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("max_attempts", 1)
        super().__init__(*args, **kwargs)


base_entry.BalatroAgentSupervisor = OneAttemptBalatroAgentSupervisor


if __name__ == "__main__":
    raise SystemExit(base_entry.main())
