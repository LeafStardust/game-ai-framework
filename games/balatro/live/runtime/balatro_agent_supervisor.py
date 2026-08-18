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

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
)
from games.balatro.live.run_experience_transition import (
    finalize_live_run,
    log_successful_live_transition,
)
from games.balatro.playbook import default_balatro_playbooks

from .agent_control import BalatroAgentControl
from .live_memory_autonomous_loop_injected import (
    AutonomousLoopRun,
    LiveMemoryInjectedAutonomousLoop,
    _terminal_stop_reason,
)
from .live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
    _action_text,
    _same_snapshot,
)
from .live_memory_restart_run_injected import (
    LiveRunRestartError,
    restart_fresh_unseeded_run,
)
from .live_memory_supervisor_observer import SupervisorLiveMemoryBalatroObserver


SESSION_SUMMARY_SCHEMA = "balatro-agent-session-summary-v1"
DEFAULT_STARTUP_STABILITY_INTERVAL_SECONDS = 0.10
DEFAULT_STARTUP_STABILITY_TIMEOUT_SECONDS = 20.0
DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS = 10.0
POST_WIN_STOP_PHASES = frozenset({"ROUND_EVAL", "GAME_OVER"})
POST_RESTART_REJECTED_STARTUP_PHASES = frozenset({"ROUND_EVAL", "GAME_OVER"})


class BalatroAgentSupervisorError(RuntimeError):
    pass


def _is_resumable_won_run(snapshot) -> bool:
    """Return whether startup is inside a manually continued Endless run.

    The first authoritative Ante-8 win checkpoint is ROUND_EVAL and must still
    auto-stop. After the user presses Continue, Balatro keeps ``won=true`` while
    returning to an actionable phase. A later agent activation may resume from
    that phase without treating the persistent win bit as a new terminal event.
    """
    return bool(snapshot.payload.get("won")) and str(snapshot.phase) not in (
        POST_WIN_STOP_PHASES
    )


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
    rejected_phases: frozenset[str] = frozenset(),
):
    """Return a settled public snapshot acceptable for attempt startup.

    Normal first attachment accepts any complete stable state so the agent can be
    enabled mid-run. After an automatic loss restart, callers reject terminal
    phases: unlock notifications are event-queue driven and a stale GAME_OVER or
    ROUND_EVAL frame can briefly resurface while the fresh run finishes settling.
    Such a frame must never become the next attempt's startup checkpoint.
    """
    if interval_seconds < 0:
        raise ValueError("startup stability interval cannot be negative")
    if timeout_seconds <= 0:
        raise ValueError("startup stability timeout must be positive")

    rejected = {str(phase) for phase in rejected_phases}

    # A fresh attempt deliberately constructs a fresh observer. Its first live
    # process-memory observation may include cold process attachment and G-table
    # discovery, which is connection cost rather than state-settling time. Start
    # the stability deadline only after that first authoritative snapshot exists.
    previous = observer.observe()
    deadline = perf_counter() + float(timeout_seconds)
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
            and str(current.phase) not in rejected
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

    Deck/stake/playbook identity is selected only after settled public observation,
    preventing a transient attachment frame from locking the supervisor to the
    wrong playbook. The production observer additionally withholds action-driving
    checkpoints until native readiness and full-state quiescence are satisfied.
    """

    def __init__(
        self,
        *,
        control: BalatroAgentControl | None = None,
        observer_factory: Callable[[], object] = SupervisorLiveMemoryBalatroObserver,
        runner_factory: Callable[[object], LiveMemoryInjectedSingleStepRunner]
        | None = None,
        restart_run: Callable[[object, str, str], object] | None = None,
        run_log_directory: str | Path = "logs/balatro/runs",
        session_directory: str | Path = "logs/balatro/sessions",
        session_id: str | None = None,
        retry_losses: bool = True,
        collection_first: bool = False,
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
            lambda observer: LiveMemoryInjectedSingleStepRunner(
                observer,
                bridge=FirstPartyBalatroBridge(
                    timeout=DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
                ),
            )
        )
        self.restart_run = restart_run or restart_fresh_unseeded_run
        self.run_log_directory = Path(run_log_directory)
        self.session_directory = Path(session_directory)
        self.session_id = str(session_id or _new_session_id())
        self.retry_losses = bool(retry_losses)
        self.collection_first = bool(collection_first)
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

    def _publish_telemetry(self, activity: str, **data) -> None:
        """Publish monitor-only activity without making monitoring mission-critical."""
        try:
            self.control.write_telemetry(
                activity,
                session_id=self.session_id,
                **data,
            )
        except (OSError, TypeError, ValueError):
            pass

    def _instrument_runner(
        self,
        runner,
        *,
        attempt_number: int,
        run_id: str,
        deck: str,
        stake: str,
    ):
        """Expose current planning/execution activity to the read-only monitor."""
        original_decide = runner.decide
        original_execute = runner.execute

        def decide_with_telemetry():
            self._publish_telemetry(
                "THINKING",
                attempt=attempt_number,
                run_id=run_id,
                deck=deck,
                stake=stake,
                detail="evaluating the current settled checkpoint",
            )
            decision = original_decide()
            self._publish_telemetry(
                "DECIDED",
                attempt=attempt_number,
                run_id=run_id,
                deck=deck,
                stake=stake,
                phase=str(decision.snapshot.phase),
                checkpoint_sequence=int(decision.snapshot.sequence),
                action=_action_text(decision),
                decision_source=str(decision.source),
                notes=[str(note) for note in decision.notes],
            )
            return decision

        def execute_with_telemetry(decision):
            action_text = _action_text(decision)
            self._publish_telemetry(
                "EXECUTING",
                attempt=attempt_number,
                run_id=run_id,
                deck=deck,
                stake=stake,
                phase=str(decision.snapshot.phase),
                checkpoint_sequence=int(decision.snapshot.sequence),
                action=action_text,
                decision_source=str(decision.source),
                notes=[str(note) for note in decision.notes],
                detail="guarding, injecting and waiting for authoritative settlement",
            )
            result, status = original_execute(decision)
            self._publish_telemetry(
                "SETTLED",
                attempt=attempt_number,
                run_id=run_id,
                deck=deck,
                stake=stake,
                phase=str(result.after.phase),
                checkpoint_sequence=int(result.after.sequence),
                action=action_text,
                decision_source=str(decision.source),
                notes=[str(note) for note in decision.notes],
                detail="previous action verified; preparing the next decision",
            )
            return result, status

        runner.decide = decide_with_telemetry
        runner.execute = execute_with_telemetry
        return runner

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
            "collection_first": self.collection_first,
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
        self.control.clear_telemetry()
        self.control.write_status(
            "ON",
            pid=pid,
            session_id=self.session_id,
            attempt=0,
            retry_losses=self.retry_losses,
            collection_first=self.collection_first,
        )
        self._publish_telemetry(
            "STARTING",
            attempt=0,
            detail="supervisor active; preparing first live attempt",
        )

        attempt_number = 1
        try:
            while True:
                if self.control.stop_requested():
                    return self._finish(won=False, stop_reason="manual stop requested")

                run_id = f"{self.session_id}-attempt-{attempt_number:03d}"
                self._publish_telemetry(
                    "ATTACHING",
                    attempt=attempt_number,
                    run_id=run_id,
                    detail="attaching observer and waiting for a settled live checkpoint",
                )
                with self.observer_factory() as observer:
                    runner = self.runner_factory(observer)
                    initial = wait_for_stable_startup_snapshot(
                        observer,
                        interval_seconds=self.startup_stability_interval_seconds,
                        timeout_seconds=self.startup_stability_timeout_seconds,
                        rejected_phases=(
                            POST_RESTART_REJECTED_STARTUP_PHASES
                            if attempt_number > 1
                            else frozenset()
                        ),
                    )
                    deck, stake, playbook = self._run_identity(initial)
                    runner = self._instrument_runner(
                        runner,
                        attempt_number=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                    )

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
                        collection_first=self.collection_first,
                    )
                    self._publish_telemetry(
                        "READY",
                        attempt=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                        phase=str(initial.phase),
                        detail="settled checkpoint verified; autonomous attempt starting",
                    )

                    initial_terminal = _terminal_stop_reason(initial)
                    if initial_terminal is not None and not _is_resumable_won_run(initial):
                        run = AutonomousLoopRun(
                            steps=(),
                            stop_reason=initial_terminal,
                        )
                    else:
                        loop = self.loop_factory(
                            runner,
                            run_id=run_id,
                            logger=self.logger_factory(run_id),
                        )
                        run = loop.run()

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
                            stop_reason=(
                                "autonomous attempt stopped without a terminal loss: "
                                + attempt.stop_reason
                            ),
                        )
                    if not self.retry_losses:
                        return self._finish(
                            won=False,
                            stop_reason="target run lost; automatic retry disabled",
                        )

                    self._publish_telemetry(
                        "RESTARTING",
                        attempt=attempt_number,
                        run_id=run_id,
                        deck=deck,
                        stake=stake,
                        detail=(
                            "loss recorded; draining unlock confirmations and requesting "
                            "fresh same-deck/stake run"
                        ),
                    )
                    try:
                        self.restart_run(runner, deck, stake)
                    except (InjectedBridgeError, LiveRunRestartError, OSError, RuntimeError) as error:
                        return self._finish(
                            won=False,
                            stop_reason=f"loss restart blocked: {error}",
                        )

                attempt_number += 1
        except Exception:
            self.control.mark_off(
                reason="supervisor crashed",
                session_id=self.session_id,
            )
            raise


class BalatroAgentSupervisorEntryPoint:
    """Production CLI wrapper around one long-lived autonomous session."""

    def __init__(self, supervisor_factory=BalatroAgentSupervisor):
        self.supervisor_factory = supervisor_factory

    def run(self, args) -> int:
        supervisor = self.supervisor_factory(
            control=BalatroAgentControl(args.control_dir),
            session_id=args.session_id,
            retry_losses=not args.no_retry_losses,
            collection_first=args.collection_first,
        )
        result = supervisor.run()
        print(
            json.dumps(
                {
                    "session_id": result.session_id,
                    "won": result.won,
                    "attempts": len(result.attempts),
                    "stop_reason": result.stop_reason,
                    "summary_path": str(result.summary_path),
                },
                sort_keys=True,
            )
        )
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one long-lived Balatro autonomous session. Losses restart fresh "
            "same-deck/stake runs; a win or manual OFF request ends the supervisor."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--session-id")
    parser.add_argument("--no-retry-losses", action="store_true")
    parser.add_argument("--collection-first", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return BalatroAgentSupervisorEntryPoint().run(args)
    except (BalatroAgentSupervisorError, OSError, RuntimeError) as error:
        print("Balatro autonomous supervisor -> FAIL")
        print(f"Reason -> {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
