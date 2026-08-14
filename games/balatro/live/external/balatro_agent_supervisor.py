from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, sleep
from typing import Callable

from games.balatro.live.injected.bridge import InjectedBridgeError
from games.balatro.live.run_experience_transition import (
    log_successful_live_transition,
)
from games.balatro.playbook import default_balatro_playbooks

from .agent_control import BalatroAgentControl
from .live_memory_autonomous_loop_injected import (
    AutonomousLoopRun,
    LiveMemoryInjectedAutonomousLoop,
)
from .live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
    _same_snapshot,
)
from .live_memory_observer import LiveMemoryBalatroObserver
from .live_memory_restart_run_injected import (
    LiveRunRestartError,
    restart_fresh_unseeded_run,
)


SESSION_SUMMARY_SCHEMA = "balatro-agent-session-summary-v1"
DEFAULT_STARTUP_STABILITY_INTERVAL_SECONDS = 0.10
DEFAULT_STARTUP_STABILITY_TIMEOUT_SECONDS = 2.0


class BalatroAgentSupervisorError(RuntimeError):
    pass


@dataclass(frozen=True)
class BalatroAgentAttempt:
    number: int
    run_id: str
    deck: str
    stake: str
    playbook: str
    playbook_version: str
    actions: int
    outcome: str
    stop_reason: str


@dataclass(frozen=True)
class BalatroAgentSessionResult:
    session_id: str
    attempts: tuple[BalatroAgentAttempt, ...]
    won: bool
    stop_reason: str
    summary_path: Path


def _new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"balatro-{stamp}-{uuid.uuid4().hex[:8]}"


def wait_for_stable_startup_snapshot(
    observer,
    *,
    interval_seconds: float = DEFAULT_STARTUP_STABILITY_INTERVAL_SECONDS,
    timeout_seconds: float = DEFAULT_STARTUP_STABILITY_TIMEOUT_SECONDS,
):
    """Return two-consecutive-equal settled public snapshots before identity lock."""
    if interval_seconds < 0:
        raise ValueError("startup stability interval cannot be negative")
    if timeout_seconds <= 0:
        raise ValueError("startup stability timeout must be positive")

    deadline = perf_counter() + float(timeout_seconds)
    previous = observer.observe()
    while True:
        if perf_counter() >= deadline:
            raise BalatroAgentSupervisorError(
                "live public state did not become semantically stable before "
                "supervisor startup identity selection"
            )
        if interval_seconds:
            sleep(interval_seconds)
        current = observer.observe()
        if (
            previous.state_complete
            and current.state_complete
            and _same_snapshot(previous, current)
        ):
            return current
        previous = current


class BalatroAgentSupervisor:
    """Long-lived ON/OFF supervisor around disposable Balatro run attempts.

    One supervisor process remains alive for the whole ON period. Each loss closes
    the current observer/run session and starts a fresh attempt after the validated
    native restart transition succeeds. Every attempt gets its own JSONL run log.
    A win ends the supervisor automatically. A manual OFF request is cooperative:
    the underlying autonomous loop stops before submitting another gameplay action.

    Deck/stake/playbook identity is selected only after two consecutive settled
    public snapshots are semantically equal, preventing a transient attachment
    frame from locking the supervisor to the wrong playbook.
    """

    def __init__(
        self,
        *,
        control: BalatroAgentControl | None = None,
        observer_factory: Callable[[], object] = LiveMemoryBalatroObserver,
        runner_factory: Callable[[object], LiveMemoryInjectedSingleStepRunner]
        | None = None,
        restart_run: Callable[[object, str, str], object] | None = None,
        run_log_directory: str | Path = "logs/balatro/runs",
        session_directory: str | Path = "logs/balatro/sessions",
        session_id: str | None = None,
        retry_losses: bool = True,
        startup_stability_interval_seconds: float = (
            DEFAULT_STARTUP_STABILITY_INTERVAL_SECONDS
        ),
        startup_stability_timeout_seconds: float = (
            DEFAULT_STARTUP_STABILITY_TIMEOUT_SECONDS
        ),
    ) -> None:
        if startup_stability_interval_seconds < 0:
            raise ValueError("startup stability interval cannot be negative")
        if startup_stability_timeout_seconds <= 0:
            raise ValueError("startup stability timeout must be positive")
        self.control = control or BalatroAgentControl()
        self.observer_factory = observer_factory
        self.runner_factory = runner_factory or (
            lambda observer: LiveMemoryInjectedSingleStepRunner(observer)
        )
        self.restart_run = restart_run or restart_fresh_unseeded_run
        self.run_log_directory = Path(run_log_directory)
        self.session_directory = Path(session_directory)
        self.session_id = str(session_id or _new_session_id())
        self.retry_losses = bool(retry_losses)
        self.startup_stability_interval_seconds = float(
            startup_stability_interval_seconds
        )
        self.startup_stability_timeout_seconds = float(
            startup_stability_timeout_seconds
        )
        self._attempts: list[BalatroAgentAttempt] = []
        self._target_deck: str | None = None
        self._target_stake: str | None = None

    @property
    def summary_path(self) -> Path:
        return self.session_directory / f"{self.session_id}.summary.json"

    def _write_summary(self, *, won: bool, stop_reason: str) -> Path:
        self.session_directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SESSION_SUMMARY_SCHEMA,
            "session_id": self.session_id,
            "won": bool(won),
            "stop_reason": str(stop_reason),
            "attempt_count": len(self._attempts),
            "loss_count": sum(1 for item in self._attempts if item.outcome == "LOSS"),
            "attempts": [asdict(item) for item in self._attempts],
            "target_deck": self._target_deck,
            "target_stake": self._target_stake,
        }
        temporary = self.summary_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, self.summary_path)
        return self.summary_path

    def _finish(self, *, won: bool, stop_reason: str) -> BalatroAgentSessionResult:
        summary_path = self._write_summary(won=won, stop_reason=stop_reason)
        self.control.mark_off(
            reason=stop_reason,
            session_id=self.session_id,
            won=bool(won),
            attempts=len(self._attempts),
            summary_path=str(summary_path),
        )
        return BalatroAgentSessionResult(
            session_id=self.session_id,
            attempts=tuple(self._attempts),
            won=bool(won),
            stop_reason=str(stop_reason),
            summary_path=summary_path,
        )

    def _run_identity(self, snapshot):
        deck = str(snapshot.payload.get("deck") or "").upper()
        stake = str(snapshot.payload.get("stake") or "").upper()
        if not deck or not stake:
            raise BalatroAgentSupervisorError(
                "live snapshot does not expose deck/stake identity"
            )
        playbook = default_balatro_playbooks().get(deck, stake)

        if self._target_deck is None:
            self._target_deck = deck
            self._target_stake = stake
        elif (deck, stake) != (self._target_deck, self._target_stake):
            raise BalatroAgentSupervisorError(
                "retry attempt changed deck/stake: expected "
                f"{self._target_deck}/{self._target_stake}, observed {deck}/{stake}"
            )
        return deck, stake, playbook

    def _record_attempt(
        self,
        *,
        number: int,
        run_id: str,
        deck: str,
        stake: str,
        playbook,
        run: AutonomousLoopRun,
    ) -> BalatroAgentAttempt:
        if run.stop_reason == "game over (won)":
            outcome = "WIN"
        elif run.stop_reason == "game over (lost)":
            outcome = "LOSS"
        elif run.stop_reason == "stop requested":
            outcome = "STOPPED"
        else:
            outcome = "BLOCKED"
        item = BalatroAgentAttempt(
            number=number,
            run_id=run_id,
            deck=deck,
            stake=stake,
            playbook=str(playbook.name),
            playbook_version=str(playbook.version),
            actions=len(run.steps),
            outcome=outcome,
            stop_reason=run.stop_reason,
        )
        self._attempts.append(item)
        return item

    def run(self) -> BalatroAgentSessionResult:
        pid = self.control.claim_current_process()
        self.control.write_status(
            "ON",
            pid=pid,
            session_id=self.session_id,
            attempt=0,
            retry_losses=self.retry_losses,
        )

        attempt_number = 1
        try:
            while True:
                if self.control.stop_requested():
                    return self._finish(won=False, stop_reason="manual stop requested")

                run_id = f"{self.session_id}-attempt-{attempt_number:03d}"
                with self.observer_factory() as observer:
                    runner = self.runner_factory(observer)
                    initial = wait_for_stable_startup_snapshot(
                        observer,
                        interval_seconds=self.startup_stability_interval_seconds,
                        timeout_seconds=self.startup_stability_timeout_seconds,
                    )
                    deck, stake, playbook = self._run_identity(initial)

                    self.control.write_status(
                        "ON",
                        pid=pid,
                        session_id=self.session_id,
                        attempt=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                        playbook=str(playbook.name),
                        playbook_version=str(playbook.version),
                        phase=str(initial.phase),
                        retry_losses=self.retry_losses,
                    )

                    if str(initial.phase) == "GAME_OVER":
                        won = bool(initial.payload.get("won"))
                        run = AutonomousLoopRun(
                            (),
                            "game over (won)" if won else "game over (lost)",
                        )
                    else:
                        def log_transition(decision, result, _status):
                            log_successful_live_transition(
                                decision,
                                result,
                                run_id=run_id,
                                directory=self.run_log_directory,
                            )

                        loop = LiveMemoryInjectedAutonomousLoop(
                            runner,
                            max_steps=None,
                            stop_requested=self.control.stop_requested,
                            on_transition=log_transition,
                        )
                        run = loop.execute(expected_start_phase=str(initial.phase))

                    attempt = self._record_attempt(
                        number=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                        playbook=playbook,
                        run=run,
                    )

                    if attempt.outcome == "WIN":
                        return self._finish(
                            won=True,
                            stop_reason="target run won; auto-off",
                        )
                    if attempt.outcome == "STOPPED":
                        return self._finish(
                            won=False,
                            stop_reason="manual stop requested",
                        )
                    if attempt.outcome != "LOSS":
                        return self._finish(
                            won=False,
                            stop_reason=run.stop_reason,
                        )
                    if not self.retry_losses:
                        return self._finish(
                            won=False,
                            stop_reason="run lost; retry disabled",
                        )

                    self.control.write_status(
                        "RESTARTING",
                        pid=pid,
                        session_id=self.session_id,
                        attempt=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                    )
                    try:
                        self.restart_run(runner, deck, stake)
                    except (LiveRunRestartError, InjectedBridgeError) as error:
                        return self._finish(
                            won=False,
                            stop_reason=f"RESTART_FAILED: {error}",
                        )

                attempt_number += 1
        except Exception as error:
            self.control.mark_off(
                reason=f"supervisor failure: {error}",
                session_id=self.session_id,
                won=False,
                attempts=len(self._attempts),
            )
            raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the toggleable Balatro autonomous supervisor. It auto-selects the "
            "deck/stake playbook from a stable public checkpoint, runs each attempt "
            "until terminal or safe stop, retries fresh same-deck/stake attempts "
            "after losses, and automatically disables itself after the first win."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    parser.add_argument("--session-directory", default="logs/balatro/sessions")
    parser.add_argument("--session-id")
    parser.add_argument("--no-retry-losses", action="store_true")
    args = parser.parse_args()

    control = BalatroAgentControl(args.control_dir)
    supervisor = BalatroAgentSupervisor(
        control=control,
        run_log_directory=args.run_log_directory,
        session_directory=args.session_directory,
        session_id=args.session_id,
        retry_losses=not args.no_retry_losses,
    )

    try:
        result = supervisor.run()
    except Exception as error:
        print("Balatro autonomous supervisor -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print("Balatro autonomous supervisor -> OFF")
    print(f"Session -> {result.session_id}")
    print(f"Attempts -> {len(result.attempts)}")
    print(f"Won -> {result.won}")
    print(f"Stop reason -> {result.stop_reason}")
    print(f"Session summary -> {result.summary_path}")
    if result.stop_reason.startswith("RESTART_FAILED:"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
