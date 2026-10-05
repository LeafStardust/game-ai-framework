"""Diagnostic-only timing attribution for the first Red/White PPO batch."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import multiprocessing
from time import perf_counter
from typing import Callable

from games.balatro.env.ppo_batch import PPOBatchAssembler
from games.balatro.env.ppo_campaign import make_ppo_training_environment
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.ppo_training_session import (
    PPOCollectedEpisode,
    PPOEpisodeRequest,
)


PPO_INITIAL_BATCH_TIMING_SCHEMA = "balatro-red-white-ppo-initial-batch-timing-v1"


def _elapsed(start: object, end: object, label: str) -> float:
    for value in (start, end):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PPOContractError(f"{label} clock sample is not numeric")
        if not math.isfinite(float(value)):
            raise PPOContractError(f"{label} clock sample is not finite")
    result = float(end) - float(start)
    if result < 0.0:
        raise PPOContractError(f"{label} clock moved backwards")
    return result


@dataclass(frozen=True)
class TimedPPOCollectedEpisode:
    collected: PPOCollectedEpisode
    elapsed_seconds: float


@dataclass(frozen=True)
class PPOEpisodeTiming:
    episode_index: int
    stream_index: int
    game_seed: str
    action_count: int
    terminal_status: str
    episode_sha256: str
    policy_parameter_sha256: str
    elapsed_seconds: float
    committed: bool


@dataclass(frozen=True)
class PPOWaveTiming:
    wave_index: int
    requested_episode_indices: tuple[int, ...]
    committed_episode_indices: tuple[int, ...]
    elapsed_seconds: float
    episodes: tuple[PPOEpisodeTiming, ...]


@dataclass(frozen=True)
class PPOInitialBatchTimingReport:
    schema: str
    training_run_sha256: str
    policy_parameter_sha256: str
    maximum_workers: int
    elapsed_seconds: float
    committed_episode_count: int
    collected_episode_count: int
    collected_environment_transitions: int
    queued_transition_counts: tuple[int, ...]
    carryover_counts: tuple[int, ...]
    next_episode_indices: tuple[int, ...]
    waves: tuple[PPOWaveTiming, ...]

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def _collect_timed_production_episode(
    request: PPOEpisodeRequest,
    training_run: PPOTrainingRun,
    model,
    *,
    clock: Callable[[], float] = perf_counter,
    environment_factory=make_ppo_training_environment,
    episode_collector=collect_complete_ppo_episode,
) -> TimedPPOCollectedEpisode:
    if not isinstance(request, PPOEpisodeRequest):
        raise TypeError("request must be PPOEpisodeRequest")
    if not callable(clock):
        raise TypeError("clock must be callable")
    policy_sha256 = getattr(model, "parameter_sha256", None)
    started = clock()
    environment = environment_factory(request.stream_index)
    episode = episode_collector(
        environment,
        training_run,
        episode_index=request.episode_index,
        policy=model.infer,
    )
    elapsed = _elapsed(started, clock(), "PPO episode timing")
    if getattr(model, "parameter_sha256", None) != policy_sha256:
        raise PPOContractError("PPO timing worker policy changed during collection")
    return TimedPPOCollectedEpisode(
        PPOCollectedEpisode(request, policy_sha256, episode), elapsed
    )


def _collect_timed_production_wave(
    executor: ProcessPoolExecutor,
    requests: tuple[PPOEpisodeRequest, ...],
    training_run: PPOTrainingRun,
    model,
) -> tuple[TimedPPOCollectedEpisode, ...]:
    futures = tuple(
        executor.submit(
            _collect_timed_production_episode,
            request,
            training_run,
            model,
        )
        for request in requests
    )
    return tuple(future.result() for future in futures)


def _require_timed_wave(
    values: object,
    requests: tuple[PPOEpisodeRequest, ...],
    *,
    policy_sha256: str,
) -> tuple[TimedPPOCollectedEpisode, ...]:
    if not isinstance(values, tuple) or len(values) != len(requests):
        raise PPOContractError("PPO timing collector returned a partial wave")
    for request, value in zip(requests, values, strict=True):
        if not isinstance(value, TimedPPOCollectedEpisode):
            raise PPOContractError("PPO timing collector result is malformed")
        collected = value.collected
        if not isinstance(collected, PPOCollectedEpisode):
            raise PPOContractError("PPO timing collector episode wrapper is malformed")
        if collected.request != request:
            raise PPOContractError("PPO timing collector order drifted")
        if collected.policy_parameter_sha256 != policy_sha256:
            raise PPOContractError("PPO timing collector policy version drifted")
        if (
            not isinstance(collected.episode, PPORolloutEpisode)
            or collected.episode.episode_index != request.episode_index
        ):
            raise PPOContractError("PPO timing collector episode provenance drifted")
        _elapsed(0.0, value.elapsed_seconds, "PPO episode timing")
    return values


def measure_initial_batch_timing(
    root_seed: str | int,
    *,
    maximum_episodes: int,
    maximum_workers: int,
    clock: Callable[[], float] = perf_counter,
    episode_wave_collector=None,
) -> PPOInitialBatchTimingReport:
    """Time exact initial-policy waves until the first batch is ready.

    This diagnostic never assembles or optimizes the ready batch. Timing is
    retained only in the returned report and cannot enter deterministic learner
    or campaign state.
    """
    if (
        isinstance(maximum_episodes, bool)
        or not isinstance(maximum_episodes, int)
        or maximum_episodes <= 0
    ):
        raise PPOContractError("PPO timing maximum episodes must be positive")
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= PPO_TRAINING_CONTRACT.parallel_environments
    ):
        raise PPOContractError("PPO timing maximum workers must be from 1 through 8")
    if not callable(clock):
        raise TypeError("clock must be callable")
    if episode_wave_collector is not None and not callable(episode_wave_collector):
        raise TypeError("episode_wave_collector must be callable")

    training_run = PPOTrainingRun.from_seed(root_seed)
    model = PPOActorCritic(training_run)
    policy_sha256 = model.parameter_sha256
    assembler = PPOBatchAssembler(training_run)
    wave_records: list[PPOWaveTiming] = []
    committed_count = 0
    collected_count = 0
    total_started = clock()

    def collect_until_ready(collector) -> None:
        nonlocal committed_count, collected_count
        while committed_count < maximum_episodes and not assembler.ready:
            wave_size = min(
                PPO_TRAINING_CONTRACT.parallel_environments,
                maximum_episodes - committed_count,
            )
            ordered_indices = sorted(assembler.next_episode_indices)
            requests = tuple(
                PPOEpisodeRequest(index % 8, index)
                for index in ordered_indices[:wave_size]
            )
            wave_started = clock()
            timed = _require_timed_wave(
                collector(requests, training_run, model),
                requests,
                policy_sha256=policy_sha256,
            )
            wave_elapsed = _elapsed(wave_started, clock(), "PPO wave timing")
            if model.parameter_sha256 != policy_sha256:
                raise PPOContractError("PPO timing policy changed during collection")

            episode_records: list[PPOEpisodeTiming] = []
            committed_indices: list[int] = []
            for value in timed:
                episode = value.collected.episode
                committed = not assembler.ready
                if committed:
                    assembler.add_episode(episode)
                    committed_count += 1
                    committed_indices.append(episode.episode_index)
                collected_count += 1
                episode_records.append(
                    PPOEpisodeTiming(
                        episode_index=episode.episode_index,
                        stream_index=value.collected.request.stream_index,
                        game_seed=episode.game_seed,
                        action_count=episode.action_count,
                        terminal_status=episode.status.value,
                        episode_sha256=sha256(episode.to_json().encode("utf-8")).hexdigest(),
                        policy_parameter_sha256=value.collected.policy_parameter_sha256,
                        elapsed_seconds=float(value.elapsed_seconds),
                        committed=committed,
                    )
                )
            wave_records.append(
                PPOWaveTiming(
                    wave_index=len(wave_records),
                    requested_episode_indices=tuple(
                        request.episode_index for request in requests
                    ),
                    committed_episode_indices=tuple(committed_indices),
                    elapsed_seconds=wave_elapsed,
                    episodes=tuple(episode_records),
                )
            )

    if episode_wave_collector is not None:
        collect_until_ready(episode_wave_collector)
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers, mp_context=context
        ) as executor:
            collect_until_ready(
                lambda requests, run, current_model: _collect_timed_production_wave(
                    executor, requests, run, current_model
                )
            )

    elapsed = _elapsed(total_started, clock(), "PPO initial-batch timing")
    if not assembler.ready:
        raise PPOContractError(
            "PPO timing episode bound ended before the first batch was ready"
        )
    queued_counts = assembler.carryover_counts
    per_stream = PPO_TRAINING_CONTRACT.rollout_steps_per_environment
    carryover_counts = tuple(count - per_stream for count in queued_counts)
    if any(count < 0 for count in carryover_counts):
        raise PPOContractError("PPO timing ready batch has invalid stream accounting")
    return PPOInitialBatchTimingReport(
        schema=PPO_INITIAL_BATCH_TIMING_SCHEMA,
        training_run_sha256=training_run.sha256,
        policy_parameter_sha256=policy_sha256,
        maximum_workers=maximum_workers,
        elapsed_seconds=elapsed,
        committed_episode_count=committed_count,
        collected_episode_count=collected_count,
        collected_environment_transitions=sum(queued_counts),
        queued_transition_counts=queued_counts,
        carryover_counts=carryover_counts,
        next_episode_indices=assembler.next_episode_indices,
        waves=tuple(wave_records),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--maximum-episodes", required=True, type=int)
    parser.add_argument("--maximum-workers", required=True, type=int)
    arguments = parser.parse_args(argv)
    report = measure_initial_batch_timing(
        arguments.root_seed,
        maximum_episodes=arguments.maximum_episodes,
        maximum_workers=arguments.maximum_workers,
    )
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
