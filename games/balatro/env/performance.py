"""Reproducible performance measurements for the exact headless environment."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from time import perf_counter

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.blind_start import start_pristine_first_small_blind
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


HEADLESS_STEPS_WORKLOAD = "red-white-pristine-small-blind-start-v1"
HEADLESS_THROUGHPUT_SCHEMA = "balatro-r6-headless-throughput-v1"


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--measured-steps", type=int, default=1000)
    args = parser.parse_args(argv)
    report = measure_headless_steps_per_second(
        warmup_steps=args.warmup_steps,
        measured_steps=args.measured_steps,
    )
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
