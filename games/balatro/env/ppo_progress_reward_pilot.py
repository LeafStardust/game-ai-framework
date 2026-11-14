"""One-batch isolated learning-signal pilot for the optional progress reward."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Callable, Sequence

import numpy as np

from games.balatro.env.ppo_campaign import (
    CHECKPOINT_NAME,
    PROGRESS_NAME,
    _atomic_write,
    run_ppo_campaign,
)
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_REWARD_CONTRACT,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic, compute_gae


PPO_PROGRESS_REWARD_PILOT_SCHEMA = "balatro-red-white-progress-reward-pilot-v1"
PILOT_REPORT_NAME = "progress_reward_pilot_report.json"


def _finite_elapsed(start: object, end: object) -> float:
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in (start, end)
    ):
        raise PPOContractError("PPO progress pilot clock sample is invalid")
    elapsed = float(end) - float(start)
    if elapsed < 0.0:
        raise PPOContractError("PPO progress pilot clock moved backwards")
    return elapsed


def _summary(values: Sequence[float], label: str) -> dict[str, float | int]:
    if not values or any(not math.isfinite(float(value)) for value in values):
        raise PPOContractError(f"PPO progress pilot {label} samples are invalid")
    numbers = tuple(float(value) for value in values)
    mean = math.fsum(numbers) / len(numbers)
    variance = math.fsum((value - mean) ** 2 for value in numbers) / len(numbers)
    return {
        "count": len(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers),
        "mean": mean,
        "variance": variance,
    }


@dataclass(frozen=True)
class PPOProgressRewardPilotReport:
    schema: str
    training_contract_sha256: str
    reward_contract: str
    training_run_sha256: str
    initial_policy_parameter_sha256: str
    final_policy_parameter_sha256: str
    checkpoint_sha256: str
    progress_sha256: str
    completed_batch_count: int
    optimizer_consumed_transitions: int
    collected_environment_transitions: int
    committed_episode_count: int
    terminal_status_counts: dict[str, int]
    reward_statistics: dict[str, float | int]
    advantage_statistics: dict[str, float | int]
    episode_depth_statistics: dict[str, float | int]
    elapsed_seconds: float
    fail_closed_counts: dict[str, int]

    def to_json(self) -> str:
        return json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def run_progress_reward_pilot(
    root_seed: str | int,
    artifact_directory: str | Path,
    *,
    maximum_episodes: int,
    maximum_workers: int,
    clock: Callable[[], float] = perf_counter,
    campaign_runner=run_ppo_campaign,
) -> PPOProgressRewardPilotReport:
    """Run exactly one fresh v2 optimizer batch and report its learning signal."""
    if not callable(clock):
        raise TypeError("clock must be callable")
    if not callable(campaign_runner):
        raise TypeError("campaign_runner must be callable")
    directory = Path(artifact_directory)
    if directory.exists():
        if not directory.is_dir():
            raise PPOContractError("PPO progress pilot artifact path is not a directory")
        try:
            if any(directory.iterdir()):
                raise PPOContractError(
                    "PPO progress pilot requires a fresh empty artifact directory"
                )
        except OSError as error:
            raise PPOContractError(
                "PPO progress pilot artifact directory is unreadable"
            ) from error
    else:
        directory.mkdir(parents=True)

    training_run = PPOTrainingRun.from_seed(
        root_seed, contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial_policy_sha256 = PPOActorCritic(training_run).parameter_sha256
    rewards: list[float] = []
    advantages: list[float] = []
    depths: list[float] = []
    terminal_statuses: Counter[str] = Counter()
    final_policy_sha256: str | None = None

    def observe(session, episode: PPORolloutEpisode) -> None:
        nonlocal final_policy_sha256
        if not isinstance(episode, PPORolloutEpisode):
            raise PPOContractError("PPO progress pilot observed an invalid episode")
        if episode.training_run != training_run:
            raise PPOContractError("PPO progress pilot episode provenance mismatch")
        episode_rewards = np.asarray(episode.rewards, dtype=np.float64)
        values = np.asarray(
            [decision.value_estimate for decision in episode.decisions],
            dtype=np.float64,
        )
        terminals = np.zeros(episode.action_count, dtype=np.bool_)
        terminals[-1] = True
        episode_advantages, _ = compute_gae(episode_rewards, values, terminals)
        rewards.extend(float(value) for value in episode_rewards)
        advantages.extend(float(value) for value in episode_advantages)
        depths.append(float(episode.action_count))
        terminal_statuses[episode.status.value] += 1
        final_policy_sha256 = session.learner.model.parameter_sha256

    started = clock()
    progress = campaign_runner(
        root_seed,
        directory,
        maximum_episodes=maximum_episodes,
        maximum_batches=1,
        maximum_workers=maximum_workers,
        training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        episode_commit_observer=observe,
    )
    elapsed = _finite_elapsed(started, clock())
    if not isinstance(progress, dict):
        raise PPOContractError("PPO progress pilot campaign result is malformed")
    if progress.get("training_run_sha256") != training_run.sha256:
        raise PPOContractError("PPO progress pilot campaign provenance mismatch")
    if progress.get("completed_batch_count") != 1:
        raise PPOContractError("PPO progress pilot did not complete exactly one batch")
    expected_transitions = PPO_PROGRESS_TRAINING_CONTRACT.rollout_batch_size
    if progress.get("optimizer_consumed_transitions") != expected_transitions:
        raise PPOContractError("PPO progress pilot optimizer transition count drifted")
    collected = progress.get("collected_environment_transitions")
    if (
        isinstance(collected, bool)
        or not isinstance(collected, int)
        or collected < expected_transitions
    ):
        raise PPOContractError("PPO progress pilot collected transition count drifted")
    if not rewards or not advantages or not depths or final_policy_sha256 is None:
        raise PPOContractError("PPO progress pilot collected no reportable signal")
    if final_policy_sha256 == initial_policy_sha256:
        raise PPOContractError("PPO progress pilot policy parameters did not update")

    checkpoint_path = directory / CHECKPOINT_NAME
    progress_path = directory / PROGRESS_NAME
    try:
        checkpoint_bytes = checkpoint_path.read_bytes()
        progress_bytes = progress_path.read_bytes()
    except OSError as error:
        raise PPOContractError("PPO progress pilot campaign artifacts are unreadable") from error
    checkpoint_sha256 = sha256(checkpoint_bytes).hexdigest()
    if progress.get("checkpoint_sha256") != checkpoint_sha256:
        raise PPOContractError("PPO progress pilot checkpoint linkage mismatch")

    fail_closed_counts = {
        "campaign_abort_count": 0,
        "nonfinite_advantage_count": 0,
        "nonfinite_reward_count": 0,
        "reward_contract_mismatch_count": 0,
        "truncated_episode_count": 0,
        "unsupported_mechanic_count": 0,
    }
    report = PPOProgressRewardPilotReport(
        schema=PPO_PROGRESS_REWARD_PILOT_SCHEMA,
        training_contract_sha256=PPO_PROGRESS_TRAINING_CONTRACT.sha256,
        reward_contract=PPO_PROGRESS_REWARD_CONTRACT,
        training_run_sha256=training_run.sha256,
        initial_policy_parameter_sha256=initial_policy_sha256,
        final_policy_parameter_sha256=final_policy_sha256,
        checkpoint_sha256=checkpoint_sha256,
        progress_sha256=sha256(progress_bytes).hexdigest(),
        completed_batch_count=1,
        optimizer_consumed_transitions=expected_transitions,
        collected_environment_transitions=collected,
        committed_episode_count=len(depths),
        terminal_status_counts=dict(sorted(terminal_statuses.items())),
        reward_statistics=_summary(rewards, "reward"),
        advantage_statistics=_summary(advantages, "advantage"),
        episode_depth_statistics=_summary(depths, "episode depth"),
        elapsed_seconds=elapsed,
        fail_closed_counts=fail_closed_counts,
    )
    _atomic_write(directory / PILOT_REPORT_NAME, report.to_json().encode("utf-8"))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--maximum-episodes", required=True, type=int)
    parser.add_argument("--maximum-workers", required=True, type=int)
    arguments = parser.parse_args(argv)
    report = run_progress_reward_pilot(
        arguments.root_seed,
        arguments.artifact_directory,
        maximum_episodes=arguments.maximum_episodes,
        maximum_workers=arguments.maximum_workers,
    )
    report_path = Path(arguments.artifact_directory) / PILOT_REPORT_NAME
    print(
        json.dumps(
            {
                "schema": report.schema,
                "report_path": str(report_path),
                "report_sha256": sha256(report_path.read_bytes()).hexdigest(),
                "completed_batch_count": report.completed_batch_count,
                "elapsed_seconds": report.elapsed_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
