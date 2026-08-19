from __future__ import annotations

from .balatro_agent_supervisor import BalatroAgentSupervisor


DEFAULT_MAX_ATTEMPTS = 10


class BoundedBalatroAgentSupervisor(BalatroAgentSupervisor):
    """Supervisor variant that stops cleanly after a bounded number of attempts.

    Wins retain the normal immediate auto-off behavior. Losses retry normally until
    the cap is reached. After the final allowed loss, no fresh run is started; the
    supervisor marks itself OFF and leaves every attempt log/session summary intact.
    """

    def __init__(self, *args, max_attempts: int = DEFAULT_MAX_ATTEMPTS, **kwargs) -> None:
        max_attempts = int(max_attempts)
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.max_attempts = max_attempts
        super().__init__(*args, **kwargs)

        original_restart = self.restart_run

        def bounded_restart(runner, deck: str, stake: str):
            if len(self._attempts) >= self.max_attempts:
                # The base run loop checks stop_requested at the top of the next
                # iteration. Do not restart Balatro here: attempt N is already
                # complete and the requested contract is to stop before N+1.
                self.control.request_stop()
                return None
            return original_restart(runner, deck, stake)

        self.restart_run = bounded_restart

    def _finish(self, *, won: bool, stop_reason: str):
        if (
            not won
            and len(self._attempts) >= self.max_attempts
            and stop_reason == "manual stop requested"
        ):
            stop_reason = (
                f"attempt limit reached ({self.max_attempts}); auto-off before next run"
            )
        return super()._finish(won=won, stop_reason=stop_reason)

    def _write_summary(self, *, won: bool, stop_reason: str):
        path = super()._write_summary(won=won, stop_reason=stop_reason)
        # The normal summary already contains every attempt. The bounded mode is
        # additionally visible in control telemetry/status, so no schema fork is
        # needed just to retain the cap.
        return path
