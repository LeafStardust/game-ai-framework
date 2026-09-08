from __future__ import annotations

from . import balatro_agent_supervisor_entry as base_entry
from .balatro_agent_bounded_supervisor import BoundedBalatroAgentSupervisor
from .live_memory_restart_run_injected import restart_fresh_unseeded_run


# Current five-run telemetry shows healthy loss->next-attempt restarts settling in
# about nine seconds, while failed restart windows can otherwise consume 60 seconds
# per bounded recovery attempt. Give the normal transition a six-second margin, then
# let the existing safe bounded recovery retry from an authoritative GAME_OVER frame.
# This caps one failed low-level restart window at 15 seconds without weakening the
# no-double-restart guard after Balatro has left GAME_OVER.
FIVE_ATTEMPT_RESTART_TIMEOUT_SECONDS = 15.0


def _five_attempt_restart(runner, deck: str, stake: str):
    return restart_fresh_unseeded_run(
        runner,
        deck,
        stake,
        timeout_seconds=FIVE_ATTEMPT_RESTART_TIMEOUT_SECONDS,
    )


class FiveAttemptBalatroAgentSupervisor(BoundedBalatroAgentSupervisor):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("restart_run", _five_attempt_restart)
        super().__init__(*args, **kwargs)


# Reuse the production supervisor entrypoint (bridge validation, diagnostics,
# collection/unlock flags, crash reports) but swap in the calibrated five-attempt
# supervisor.
base_entry.BalatroAgentSupervisor = FiveAttemptBalatroAgentSupervisor


if __name__ == "__main__":
    raise SystemExit(base_entry.main())
