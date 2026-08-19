from __future__ import annotations

from . import balatro_agent_supervisor_entry as base_entry
from .balatro_agent_bounded_supervisor import BoundedBalatroAgentSupervisor


# Reuse the production supervisor entrypoint (bridge validation, diagnostics,
# collection/unlock flags, crash reports) but swap in the five-attempt supervisor.
base_entry.BalatroAgentSupervisor = BoundedBalatroAgentSupervisor


if __name__ == "__main__":
    raise SystemExit(base_entry.main())
