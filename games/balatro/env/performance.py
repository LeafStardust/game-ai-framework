"""Reproducible performance measurements for the exact headless environment."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from time import perf_counter
from types import SimpleNamespace
from typing import Any

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.blind_start import start_pristine_first_small_blind
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


HEADLESS_STEPS_WORKLOAD = "red-white-pristine-small-blind-start-v1"
HEADLESS_THROUGHPUT_SCHEMA = "balatro-r6-headless-throughput-v1"
COMPLETE_RUNS_WORKLOAD = "red-white-first-small-blind-single-card-loss-v1"
COMPLETE_RUNS_THROUGHPUT_SCHEMA = "balatro-r6-complete-runs-throughput-v1"
PARALLEL_SCALING_SCHEMA = "balatro-r6-parallel-scaling-v1"
TACTICAL_BRIDGE_WORKLOAD = "red-white-first-small-blind-first-card-play-v1"
TACTICAL_BRIDGE_COST_SCHEMA = "balatro-r6-tactical-bridge-cost-v1"


@dataclass(frozen=True)
class HeadlessThroughputReport:
    schema: str
    workload: str
    warmup_steps: int
    measured_steps: int
    elapsed_seconds: float
    steps_per_second: float

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class CompleteRunsThroughputReport:
    schema: str
    workload: str
    warmup_runs: int
    measured_runs: int
    completed_runs: int
    elapsed_seconds: float
    runs_per_minute: float

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class ParallelScalingSample:
    workers: int
    warmup_runs_per_worker: int
    measured_runs: int
    completed_runs: int
    elapsed_seconds: float
    runs_per_minute: float
    scaling: float
    efficiency: float


@dataclass(frozen=True)
class ParallelScalingReport:
    schema: str
    workload: str
    samples: tuple[ParallelScalingSample, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class TacticalBridgeCostReport:
    schema: str
    workload: str
    warmup_steps: int
    measured_steps: int
    direct_elapsed_seconds: float
    bridged_elapsed_seconds: float
    direct_steps_per_second: float
    bridged_steps_per_second: float
    overhead_seconds_per_step: float
    overhead_ratio: float

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


def _step_count(value: int, *, name: str, allow_zero: bool) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        qualifier = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a {qualifier} integer")
    return value


def _pristine_small_blind_template() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 0
    state.blind = create_small_blind(300)
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="R6-HEADLESS-STEPS")


def measure_headless_steps_per_second(
    *,
    warmup_steps: int = 100,
    measured_steps: int = 1000,
    clock: Callable[[], float] = perf_counter,
) -> HeadlessThroughputReport:
    """Measure one fixed canonical Red/White headless transition workload.

    Each step starts from the same immutable pre-action template and executes
    the production pristine Small-Blind start owner. Reusing the template is
    intentional: the owner isolates its output, so the timed work includes its
    real state/RNG copy and exact lifecycle, shuffle, deal, and facing updates.
    """
    warmup_steps = _step_count(warmup_steps, name="warmup_steps", allow_zero=True)
    measured_steps = _step_count(
        measured_steps,
        name="measured_steps",
        allow_zero=False,
    )
    if not callable(clock):
        raise TypeError("clock must be callable")

    template = _pristine_small_blind_template()
    for _ in range(warmup_steps):
        start_pristine_first_small_blind(template)

    started = float(clock())
    result = None
    for _ in range(measured_steps):
        result = start_pristine_first_small_blind(template)
    elapsed = float(clock()) - started

    if not math.isfinite(elapsed) or elapsed <= 0.0:
        raise RuntimeError("headless throughput clock must report positive finite elapsed time")
    if (
        result is None
        or result.public.phase != "SELECTING_HAND"
        or len(result.public.hand) != 8
        or len(result.draw_pile) != 44
    ):
        raise RuntimeError("headless throughput workload produced an invalid result")

    return HeadlessThroughputReport(
        schema=HEADLESS_THROUGHPUT_SCHEMA,
        workload=HEADLESS_STEPS_WORKLOAD,
        warmup_steps=warmup_steps,
        measured_steps=measured_steps,
        elapsed_seconds=elapsed,
        steps_per_second=measured_steps / elapsed,
    )


def run_fixed_red_white_episode() -> HeadlessRunState:
    """Run one exact fixed Red/White episode to an authoritative loss.

    The workload starts at the fresh first-Small-Blind choice boundary and uses
    the canonical production transition owners throughout. It deliberately
    plays one visible card per hand so the fixed seed cannot clear the 300-chip
    blind before all four Red/White hands are consumed. This is an honest
    complete losing episode, not a substitute backend or a projected terminal.
    """
    run = start_pristine_first_small_blind(_pristine_small_blind_template())
    actions = 0
    while run.public.phase == "SELECTING_HAND":
        run = apply_supported_ordinary_play(run, (0,))
        actions += 1

    _require_fixed_episode_terminal(run)
    if actions != 4:
        raise RuntimeError("complete-runs workload did not reach its exact terminal loss")
    return run


def _require_fixed_episode_terminal(run: HeadlessRunState) -> None:
    if (
        not isinstance(run, HeadlessRunState)
        or run.public.phase != "GAME_OVER"
        or run.public.hands_remaining != 0
        or run.public.blind is None
        or run.public.score >= run.public.blind.requirement
    ):
        raise RuntimeError("complete-runs workload did not reach its exact terminal loss")


def measure_complete_red_white_runs_per_minute(
    *,
    warmup_runs: int = 100,
    measured_runs: int = 1000,
    clock: Callable[[], float] = perf_counter,
) -> CompleteRunsThroughputReport:
    """Measure the fixed complete canonical Red/White episode workload."""
    warmup_runs = _step_count(warmup_runs, name="warmup_runs", allow_zero=True)
    measured_runs = _step_count(
        measured_runs,
        name="measured_runs",
        allow_zero=False,
    )
    if not callable(clock):
        raise TypeError("clock must be callable")

    for _ in range(warmup_runs):
        run_fixed_red_white_episode()

    started = float(clock())
    completed_runs = 0
    for _ in range(measured_runs):
        result = run_fixed_red_white_episode()
        _require_fixed_episode_terminal(result)
        completed_runs += 1
    elapsed = float(clock()) - started

    if not math.isfinite(elapsed) or elapsed <= 0.0:
        raise RuntimeError(
            "complete-runs throughput clock must report positive finite elapsed time"
        )
    if completed_runs != measured_runs:
        raise RuntimeError("complete-runs workload did not complete every measured episode")

    return CompleteRunsThroughputReport(
        schema=COMPLETE_RUNS_THROUGHPUT_SCHEMA,
        workload=COMPLETE_RUNS_WORKLOAD,
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
        completed_runs=completed_runs,
        elapsed_seconds=elapsed,
        runs_per_minute=completed_runs * 60.0 / elapsed,
    )


def _run_fixed_episode_batch(run_count: int) -> int:
    completed = 0
    for _ in range(run_count):
        result = run_fixed_red_white_episode()
        _require_fixed_episode_terminal(result)
        completed += 1
    return completed


def _partition_runs(measured_runs: int, workers: int) -> tuple[int, ...]:
    quotient, remainder = divmod(measured_runs, workers)
    return tuple(
        quotient + (1 if worker_index < remainder else 0)
        for worker_index in range(workers)
    )


def _completed_batch(future: Any, expected: int, *, label: str) -> int:
    completed = future.result()
    if type(completed) is not int or completed != expected:
        raise RuntimeError(f"parallel {label} did not complete every episode")
    return completed


def measure_parallel_red_white_scaling(
    *,
    worker_counts: Sequence[int] = (1, 2, 4),
    warmup_runs_per_worker: int = 10,
    measured_runs: int = 1000,
    clock: Callable[[], float] = perf_counter,
    executor_factory: Callable[[int], Any] = ProcessPoolExecutor,
) -> ParallelScalingReport:
    """Measure strong scaling over independent process-owned exact episodes."""
    counts = tuple(worker_counts)
    if (
        not counts
        or any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in counts)
        or len(counts) != len(set(counts))
        or 1 not in counts
    ):
        raise ValueError("worker_counts must contain distinct positive integers including 1")
    warmup_runs_per_worker = _step_count(
        warmup_runs_per_worker,
        name="warmup_runs_per_worker",
        allow_zero=True,
    )
    measured_runs = _step_count(measured_runs, name="measured_runs", allow_zero=False)
    if measured_runs < max(counts):
        raise ValueError("measured_runs must provide at least one run per worker")
    if not callable(clock):
        raise TypeError("clock must be callable")
    if not callable(executor_factory):
        raise TypeError("executor_factory must be callable")

    raw_samples: list[tuple[int, float, float]] = []
    for workers in counts:
        partitions = _partition_runs(measured_runs, workers)
        with executor_factory(workers) as executor:
            if warmup_runs_per_worker:
                warmups = [
                    executor.submit(_run_fixed_episode_batch, warmup_runs_per_worker)
                    for _ in range(workers)
                ]
                for future in warmups:
                    _completed_batch(
                        future,
                        warmup_runs_per_worker,
                        label="warmup",
                    )

            started = float(clock())
            futures = [
                executor.submit(_run_fixed_episode_batch, partition)
                for partition in partitions
            ]
            completed_runs = sum(
                _completed_batch(future, partition, label="workload")
                for future, partition in zip(futures, partitions, strict=True)
            )
            elapsed = float(clock()) - started

        if completed_runs != measured_runs:
            raise RuntimeError("parallel workload did not complete every measured episode")
        if not math.isfinite(elapsed) or elapsed <= 0.0:
            raise RuntimeError(
                "parallel throughput clock must report positive finite elapsed time"
            )
        raw_samples.append((workers, elapsed, completed_runs * 60.0 / elapsed))

    baseline = next(throughput for workers, _, throughput in raw_samples if workers == 1)
    samples = tuple(
        ParallelScalingSample(
            workers=workers,
            warmup_runs_per_worker=warmup_runs_per_worker,
            measured_runs=measured_runs,
            completed_runs=measured_runs,
            elapsed_seconds=elapsed,
            runs_per_minute=throughput,
            scaling=throughput / baseline,
            efficiency=(throughput / baseline) / workers,
        )
        for workers, elapsed, throughput in raw_samples
    )
    return ParallelScalingReport(
        schema=PARALLEL_SCALING_SCHEMA,
        workload=COMPLETE_RUNS_WORKLOAD,
        samples=samples,
    )


class _FirstCardPlayDecisionEngine:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


def _tactical_play_template() -> HeadlessRunState:
    return start_pristine_first_small_blind(_pristine_small_blind_template())


def _require_tactical_cost_result(run: HeadlessRunState) -> None:
    if (
        not isinstance(run, HeadlessRunState)
        or run.public.phase != "SELECTING_HAND"
        or run.public.hands_remaining != 3
        or len(run.public.hand) != 8
        or len(run.draw_pile) != 43
    ):
        raise RuntimeError("tactical cost workload produced an invalid result")


def measure_tactical_bridge_cost(
    *,
    warmup_steps: int = 100,
    measured_steps: int = 1000,
    clock: Callable[[], float] = perf_counter,
) -> TacticalBridgeCostReport:
    """Compare direct exact Play with the production-shaped decision bridge."""
    warmup_steps = _step_count(warmup_steps, name="warmup_steps", allow_zero=True)
    measured_steps = _step_count(measured_steps, name="measured_steps", allow_zero=False)
    if not callable(clock):
        raise TypeError("clock must be callable")

    template = _tactical_play_template()
    engine = _FirstCardPlayDecisionEngine()
    for _ in range(warmup_steps):
        _require_tactical_cost_result(apply_supported_ordinary_play(template, (0,)))
        _require_tactical_cost_result(apply_planned_tactical_step(template, engine))

    started = float(clock())
    for _ in range(measured_steps):
        direct_result = apply_supported_ordinary_play(template, (0,))
    direct_elapsed = float(clock()) - started

    started = float(clock())
    for _ in range(measured_steps):
        bridged_result = apply_planned_tactical_step(template, engine)
    bridged_elapsed = float(clock()) - started

    _require_tactical_cost_result(direct_result)
    _require_tactical_cost_result(bridged_result)
    if (
        canonical_public_state_signature(direct_result.public)
        != canonical_public_state_signature(bridged_result.public)
        or direct_result.rng_snapshot() != bridged_result.rng_snapshot()
    ):
        raise RuntimeError("direct and bridged tactical workloads diverged")
    if not math.isfinite(direct_elapsed) or direct_elapsed <= 0.0:
        raise RuntimeError("direct tactical clock must report positive finite elapsed time")
    if not math.isfinite(bridged_elapsed) or bridged_elapsed <= 0.0:
        raise RuntimeError("bridged tactical clock must report positive finite elapsed time")

    return TacticalBridgeCostReport(
        schema=TACTICAL_BRIDGE_COST_SCHEMA,
        workload=TACTICAL_BRIDGE_WORKLOAD,
        warmup_steps=warmup_steps,
        measured_steps=measured_steps,
        direct_elapsed_seconds=direct_elapsed,
        bridged_elapsed_seconds=bridged_elapsed,
        direct_steps_per_second=measured_steps / direct_elapsed,
        bridged_steps_per_second=measured_steps / bridged_elapsed,
        overhead_seconds_per_step=(bridged_elapsed - direct_elapsed) / measured_steps,
        overhead_ratio=bridged_elapsed / direct_elapsed - 1.0,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metric",
        choices=("steps", "runs", "parallel", "tactical"),
        default="steps",
    )
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--measured-steps", type=int, default=1000)
    parser.add_argument("--warmup-runs", type=int, default=100)
    parser.add_argument("--measured-runs", type=int, default=1000)
    parser.add_argument("--worker-counts", type=int, nargs="+", default=(1, 2, 4))
    parser.add_argument("--parallel-warmup-runs-per-worker", type=int, default=10)
    parser.add_argument("--parallel-measured-runs", type=int, default=1000)
    args = parser.parse_args(argv)
    if args.metric == "tactical":
        report = measure_tactical_bridge_cost(
            warmup_steps=args.warmup_steps,
            measured_steps=args.measured_steps,
        )
    elif args.metric == "parallel":
        report = measure_parallel_red_white_scaling(
            worker_counts=args.worker_counts,
            warmup_runs_per_worker=args.parallel_warmup_runs_per_worker,
            measured_runs=args.parallel_measured_runs,
        )
    elif args.metric == "runs":
        report = measure_complete_red_white_runs_per_minute(
            warmup_runs=args.warmup_runs,
            measured_runs=args.measured_runs,
        )
    else:
        report = measure_headless_steps_per_second(
            warmup_steps=args.warmup_steps,
            measured_steps=args.measured_steps,
        )
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
