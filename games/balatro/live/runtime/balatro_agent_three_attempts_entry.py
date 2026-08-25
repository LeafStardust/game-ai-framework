from __future__ import annotations

from . import balatro_agent_supervisor_entry as base_entry
from .balatro_agent_bounded_supervisor import BoundedBalatroAgentSupervisor
from .live_memory_restart_run_injected import restart_fresh_unseeded_run


THREE_ATTEMPT_RESTART_TIMEOUT_SECONDS = 15.0


def _three_attempt_restart(runner, deck: str, stake: str):
    return restart_fresh_unseeded_run(
        runner,
        deck,
        stake,
        timeout_seconds=THREE_ATTEMPT_RESTART_TIMEOUT_SECONDS,
    )


class ThreeAttemptBalatroAgentSupervisor(BoundedBalatroAgentSupervisor):
    """Run ordinary production policy for at most three attempts."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("max_attempts", 3)
        kwargs.setdefault("restart_run", _three_attempt_restart)
        # The low-level restart already performs guarded one-second retries for
        # its entire 15-second window. Do not multiply a failed native transition
        # into three identical 15-second windows while the monitor says RESTARTING.
        kwargs.setdefault("restart_recovery_attempts", 1)
        super().__init__(*args, **kwargs)


base_entry.BalatroAgentSupervisor = ThreeAttemptBalatroAgentSupervisor


if __name__ == "__main__":
    raise SystemExit(base_entry.main())
