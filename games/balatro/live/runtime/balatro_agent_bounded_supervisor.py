from __future__ import annotations

from time import monotonic, sleep

from games.balatro.live.injected.bridge import InjectedBridgeError

from .balatro_agent_supervisor import BalatroAgentSupervisor
from .live_memory_autonomous_step_injected import _same_snapshot
from .live_memory_restart_run_injected import LiveRunRestartError


DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_RESTART_RECOVERY_ATTEMPTS = 3
DEFAULT_POST_RESTART_RECOVERY_TIMEOUT_SECONDS = 20.0
DEFAULT_POST_RESTART_RECOVERY_POLL_SECONDS = 0.10
DEFAULT_POST_RESTART_STABLE_CONFIRMATIONS = 3


def _snapshot_identity(snapshot) -> tuple[str, str]:
    payload = getattr(snapshot, "payload", {}) or {}
    return (
        str(payload.get("deck") or "").upper(),
        str(payload.get("stake") or "").upper(),
    )


def _recover_restart_boundary(
    runner,
    deck: str,
    stake: str,
    *,
    stop_requested,
    timeout_seconds: float = DEFAULT_POST_RESTART_RECOVERY_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_POST_RESTART_RECOVERY_POLL_SECONDS,
    stable_confirmations: int = DEFAULT_POST_RESTART_STABLE_CONFIRMATIONS,
) -> str:
    """Classify a failed restart without risking a duplicate destructive restart.

    ``READY`` means Balatro already transitioned to a sustained fresh BLIND_SELECT;
    ``GAME_OVER`` means it is still safe for the caller to retry RESTART_RUN;
    ``UNRESOLVED`` means the game left GAME_OVER but did not settle to BLIND_SELECT,
    so the caller must fail closed instead of issuing another restart command.
    """
    expected = (str(deck).upper(), str(stake).upper())
    deadline = monotonic() + max(0.0, float(timeout_seconds))
    previous = None
    stable_count = 0
    saw_non_game_over = False

    while True:
        if stop_requested():
            return "UNRESOLVED"

        current = runner.observer.observe()
        phase = str(getattr(current, "phase", ""))
        complete = bool(getattr(current, "state_complete", False))
        identity = _snapshot_identity(current)

        if phase != "GAME_OVER":
            saw_non_game_over = True

        if complete and phase == "BLIND_SELECT" and identity == expected:
            if previous is not None and _same_snapshot(previous, current):
                stable_count += 1
            else:
                stable_count = 1
            previous = current
            if stable_count >= max(2, int(stable_confirmations)):
                return "READY"
        else:
            previous = None
            stable_count = 0

        # If the game is still authoritatively on the same lost GAME_OVER frame,
        # the original guarded restart routine may safely be invoked again. Return
        # immediately instead of wasting the recovery window.
        if complete and phase == "GAME_OVER" and identity == expected and not saw_non_game_over:
            return "GAME_OVER"

        if monotonic() >= deadline:
            return "UNRESOLVED"
        if poll_seconds:
            sleep(max(0.0, float(poll_seconds)))


class BoundedBalatroAgentSupervisor(BalatroAgentSupervisor):
    """Supervisor variant that stops cleanly after a bounded number of attempts.

    Wins retain the normal immediate auto-off behavior. Losses retry normally until
    the cap is reached. After the final allowed loss, no fresh run is started; the
    supervisor marks itself OFF and leaves every attempt log/session summary intact.

    Between attempts, transient restart failures get bounded recovery. A destructive
    restart is retried only while public state still proves the same lost GAME_OVER
    source is active. If Balatro already left GAME_OVER, recovery becomes read-only
    and waits for a sustained same-deck/stake BLIND_SELECT checkpoint.
    """

    def __init__(
        self,
        *args,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        restart_recovery_attempts: int = DEFAULT_RESTART_RECOVERY_ATTEMPTS,
        **kwargs,
    ) -> None:
        max_attempts = int(max_attempts)
        restart_recovery_attempts = int(restart_recovery_attempts)
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if restart_recovery_attempts <= 0:
            raise ValueError("restart_recovery_attempts must be positive")
        self.max_attempts = max_attempts
        self.restart_recovery_attempts = restart_recovery_attempts
        super().__init__(*args, **kwargs)

        original_restart = self.restart_run

        def bounded_restart(runner, deck: str, stake: str):
            if len(self._attempts) >= self.max_attempts:
                # The base run loop checks stop_requested at the top of the next
                # iteration. Do not restart Balatro here: attempt N is already
                # complete and the requested contract is to stop before N+1.
                self.control.request_stop()
                return None

            last_error: Exception | None = None
            for recovery_attempt in range(1, self.restart_recovery_attempts + 1):
                try:
                    return original_restart(runner, deck, stake)
                except (LiveRunRestartError, InjectedBridgeError) as error:
                    last_error = error
                    self._publish_telemetry(
                        "RESTART_RECOVERING",
                        attempt=len(self._attempts),
                        deck=str(deck).upper(),
                        stake=str(stake).upper(),
                        detail=(
                            f"restart boundary failure {recovery_attempt}/"
                            f"{self.restart_recovery_attempts}: {error}"
                        ),
                    )

                    boundary = _recover_restart_boundary(
                        runner,
                        deck,
                        stake,
                        stop_requested=self.control.stop_requested,
                    )
                    if boundary == "READY":
                        self._publish_telemetry(
                            "RESTART_RECOVERED",
                            attempt=len(self._attempts),
                            deck=str(deck).upper(),
                            stake=str(stake).upper(),
                            detail=(
                                "restart command had already transitioned the game; "
                                "fresh BLIND_SELECT settled without a duplicate restart"
                            ),
                        )
                        return None
                    if boundary != "GAME_OVER":
                        raise error
                    if recovery_attempt >= self.restart_recovery_attempts:
                        raise error

                    self._publish_telemetry(
                        "RESTART_RETRYING",
                        attempt=len(self._attempts),
                        deck=str(deck).upper(),
                        stake=str(stake).upper(),
                        detail=(
                            "same lost GAME_OVER remains authoritative; guarded "
                            "restart may be retried safely"
                        ),
                    )

            assert last_error is not None
            raise last_error

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
