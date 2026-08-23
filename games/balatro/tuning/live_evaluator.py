from __future__ import annotations

"""Authoritative live Balatro batch evaluation for offline numerical tuning.

Unlike ``LocalBatchEvaluator``, this adapter does not pretend the real game is
seeded.  One trial runs a bounded supervisor session under one immutable calibration
snapshot, then derives metrics only from the durable public run logs produced by
that session.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from games.balatro.bonds.calibration import BondCalibration, use_bond_calibration
from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
)
from games.balatro.tuning.live_metrics import episode_metrics_from_run_ids
from games.balatro.tuning.metrics import BatchMetrics


class SupervisorResult(Protocol):
    session_id: str
    attempts: tuple
    won: bool
    stop_reason: str


SupervisorFactory = Callable[..., object]


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
    and terminal behavior.  The tuner only supplies an immutable numerical snapshot
    and reads the normal durable logs afterward.
    """

    attempts_per_trial: int = 5
    run_log_directory: Path = Path("logs/balatro/tuning/runs")
    session_directory: Path = Path("logs/balatro/tuning/sessions")
    control_directory: Path = Path("logs/balatro/tuning/control")
    supervisor_factory: SupervisorFactory = BoundedBalatroAgentSupervisor

    def __post_init__(self) -> None:
        if int(self.attempts_per_trial) <= 0:
            raise ValueError("attempts_per_trial must be positive")

    def evaluate(self, calibration: BondCalibration) -> LiveEvaluationResult:
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

        episodes = episode_metrics_from_run_ids(
            run_ids,
            directory=self.run_log_directory,
        )
        if len(episodes) != len(run_ids):
            raise RuntimeError("live tuning run-log count does not match supervisor attempts")

        return LiveEvaluationResult(
            metrics=BatchMetrics.from_episodes(episodes),
            session_id=str(result.session_id),
            run_ids=run_ids,
            won=bool(result.won),
            stop_reason=str(result.stop_reason),
        )

    def __call__(self, calibration: BondCalibration) -> BatchMetrics:
        return self.evaluate(calibration).metrics
