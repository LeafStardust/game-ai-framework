from __future__ import annotations

"""Authoritative live Balatro batch evaluation for offline numerical tuning.

Unlike ``LocalBatchEvaluator``, this adapter does not pretend the real game is
seeded. One trial runs a bounded supervisor session under one immutable calibration
snapshot, derives metrics from the normal public logs, then restores a fresh
BLIND_SELECT boundary after a final loss so the next trial can start cleanly.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from games.balatro.bonds.calibration import BondCalibration, use_bond_calibration
from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
)
from games.balatro.tuning.live_metrics_runtime import episode_metrics_from_run_ids
from games.balatro.tuning.live_preflight import validate_live_tuning_preflight
from games.balatro.tuning.metrics import BatchMetrics


class SupervisorResult(Protocol):
    session_id: str
    attempts: tuple
    won: bool
    stop_reason: str


SupervisorFactory = Callable[..., object]
PreflightValidator = Callable[..., object]


@dataclass(frozen=True)
class LiveEvaluationResult:
    metrics: BatchMetrics
    session_id: str
    run_ids: tuple[str, ...]
    won: bool
    stop_reason: str


@dataclass(frozen=True)
class AuthoritativeLiveBatchEvaluator:
    """Run one bounded, unseeded real-game session for an Optuna trial.

    The production supervisor still owns observation, legality, execution, restart,
    and terminal behavior. The tuner only supplies an immutable numerical snapshot,
    reads the normal durable logs afterward, and restores the next fresh-run boundary
    after a completed all-loss batch.
    """

    attempts_per_trial: int = 3
    deck: str = "RED"
    stake: str = "WHITE"
    run_log_directory: Path = Path("logs/balatro/tuning/runs")
    session_directory: Path = Path("logs/balatro/tuning/sessions")
    control_directory: Path = Path("logs/balatro/tuning/control")
    supervisor_factory: SupervisorFactory = BoundedBalatroAgentSupervisor
    preflight_validator: PreflightValidator = validate_live_tuning_preflight
    reset_after_loss: bool = True

    def __post_init__(self) -> None:
        if int(self.attempts_per_trial) <= 0:
            raise ValueError("attempts_per_trial must be positive")
        if not str(self.deck).strip() or not str(self.stake).strip():
            raise ValueError("live evaluator deck/stake identity is required")

    def _preflight(self) -> object:
        return self.preflight_validator(
            expected_deck=str(self.deck).upper(),
            expected_stake=str(self.stake).upper(),
        )

    def _reset_terminal_loss(self, result: SupervisorResult) -> None:
        """Restore a fresh unseeded BLIND_SELECT after the final allowed loss."""
        if not self.reset_after_loss or bool(result.won):
            return
        attempts = tuple(result.attempts)
        if not attempts:
            return
        last = attempts[-1]
        if str(getattr(last, "outcome", "")) != "LOSS":
            raise RuntimeError(
                "live tuning batch did not end in a restartable LOSS boundary: "
                f"{getattr(last, 'outcome', None)!r}"
            )

        deck = str(getattr(last, "deck", "")).upper()
        stake = str(getattr(last, "stake", "")).upper()
        if not deck or not stake:
            raise RuntimeError("cannot reset live tuning boundary without deck/stake identity")

        expected_deck = str(self.deck).upper()
        expected_stake = str(self.stake).upper()
        if deck != expected_deck or stake != expected_stake:
            raise RuntimeError(
                "live tuning terminal identity drifted before reset: "
                f"observed {deck or '?'} / {stake or '?'}, "
                f"expected {expected_deck} / {expected_stake}"
            )

        # Only initialize the live restart machinery after the terminal attempt has
        # proven it belongs to the same deck/stake contract as this evaluator.
        from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
            LiveMemoryInjectedSingleStepRunner,
        )
        from games.balatro.live.runtime.live_memory_restart_run_injected import (
            restart_fresh_unseeded_run,
        )
        from games.balatro.live.runtime.live_memory_supervisor_observer import (
            SupervisorLiveMemoryBalatroObserver,
        )

        with SupervisorLiveMemoryBalatroObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(observer)
            restart_fresh_unseeded_run(runner, deck, stake)

    def evaluate(self, calibration: BondCalibration) -> LiveEvaluationResult:
        # Every trial, including trial 2+ after a loss reset, must prove the same
        # fresh public start boundary before any candidate calibration is applied.
        self._preflight()

        # Import locally so normal tuning metric/log parsing does not initialize the
        # live-control implementation unless a real evaluation is requested.
        from games.balatro.live.runtime.agent_control import BalatroAgentControl

        control = BalatroAgentControl(self.control_directory)
        supervisor = self.supervisor_factory(
            control=control,
            run_log_directory=self.run_log_directory,
            session_directory=self.session_directory,
            max_attempts=int(self.attempts_per_trial),
            retry_losses=True,
            collection_first=False,
        )
        with use_bond_calibration(calibration):
            result: SupervisorResult = supervisor.run()

        run_ids = tuple(str(attempt.run_id) for attempt in result.attempts)
        if not run_ids:
            raise RuntimeError(
                f"live tuning session {result.session_id!r} completed without an attempt"
            )
        if len(run_ids) > int(self.attempts_per_trial):
            raise RuntimeError("bounded live tuning supervisor exceeded its attempt cap")

        episodes = episode_metrics_from_run_ids(run_ids, directory=self.run_log_directory)
        if len(episodes) != len(run_ids):
            raise RuntimeError("live tuning run-log count does not match supervisor attempts")

        evaluation = LiveEvaluationResult(
            metrics=BatchMetrics.from_episodes(episodes),
            session_id=str(result.session_id),
            run_ids=run_ids,
            won=bool(result.won),
            stop_reason=str(result.stop_reason),
        )

        # Lost bounded batches stop before starting attempt N+1, intentionally
        # leaving GAME_OVER. Reset only after metrics/provenance are durably captured.
        # Won runs are not restartable through the guarded loss-restart API; the live
        # study runner stops after a winning trial and requires review/holdout next.
        self._reset_terminal_loss(result)
        return evaluation

    def __call__(self, calibration: BondCalibration) -> BatchMetrics:
        return self.evaluate(calibration).metrics
