"""Read-only tactical attribution for one exact restored PPO campaign episode."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Callable

from games.balatro.env.ppo_campaign import (
    PPO_CAMPAIGN_VERSION,
    _atomic_write,
    _canonical_bytes,
    _restore_session,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_campaign_wave_timing import _read_canonical_checkpoint
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_initial_batch_timing import _elapsed
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.ppo_tactical_performance import (
    PPOTacticalEpisodeDecisionCost,
    _instrument_episode_engine,
)


PPO_CHECKPOINT_TACTICAL_EPISODE_SCHEMA = (
    "balatro-red-white-ppo-checkpoint-tactical-episode-v1"
)


@dataclass(frozen=True)
class PPOCheckpointTacticalEpisodeReport:
    schema: str
    campaign_version: str
    checkpoint_sha256: str
    training_run_sha256: str
    policy_parameter_sha256: str
    session_sha256_before: str
    session_sha256_after: str
    root_seed: str | int
    episode_index: int
    stream_index: int
    game_seed: str
    episode_sha256: str
    terminal_status: str
    environment_transitions: int
    total_elapsed_seconds: float
    tactical_elapsed_seconds: float
    committed: bool
    decisions: tuple[PPOTacticalEpisodeDecisionCost, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def _validate_decision_timings(
    records: tuple[PPOTacticalEpisodeDecisionCost, ...],
) -> float:
    tactical = 0.0
    for record in records:
        buckets = (
            record.candidate_generation_elapsed_seconds,
            record.search_evaluation_elapsed_seconds,
            record.policy_arbitration_elapsed_seconds,
            record.other_elapsed_seconds,
        )
        values = (record.total_elapsed_seconds, *buckets)
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise PPOContractError(
                "PPO checkpoint tactical trace produced invalid decision timing"
            )
        if not math.isclose(sum(buckets), record.total_elapsed_seconds, abs_tol=1e-9):
            raise PPOContractError(
                "PPO checkpoint tactical trace decision timing did not balance"
            )
        tactical += record.total_elapsed_seconds
    if not math.isfinite(tactical):
        raise PPOContractError("PPO checkpoint tactical trace timing overflowed")
    return tactical


def trace_checkpoint_ppo_episode_tactical_costs(
    root_seed: str | int,
    checkpoint_path: str | Path,
    *,
    episode_index: int,
    clock: Callable[[], float] = perf_counter,
    environment_factory=make_ppo_training_environment,
    episode_collector=collect_complete_ppo_episode,
) -> PPOCheckpointTacticalEpisodeReport:
    """Trace one pending checkpoint episode without advancing campaign state."""
    if (
        isinstance(episode_index, bool)
        or not isinstance(episode_index, int)
        or episode_index < 0
    ):
        raise PPOContractError(
            "PPO checkpoint tactical trace requires a nonnegative episode index"
        )
    if not callable(clock):
        raise TypeError("clock must be callable")
    if not callable(environment_factory):
        raise TypeError("environment_factory must be callable")
    if not callable(episode_collector):
        raise TypeError("episode_collector must be callable")

    checkpoint_bytes, payload = _read_canonical_checkpoint(Path(checkpoint_path))
    checkpoint_sha256 = sha256(checkpoint_bytes).hexdigest()
    training_run = PPOTrainingRun.from_seed(root_seed)
    session = _restore_session(training_run, payload, environment_factory)
    model = session.learner.model
    policy_sha256 = model.parameter_sha256
    stream_count = PPO_TRAINING_CONTRACT.parallel_environments
    stream_index = episode_index % stream_count
    next_indices = session.learner.assembler.next_episode_indices
    if (
        len(next_indices) != stream_count
        or next_indices[stream_index] != episode_index
    ):
        raise PPOContractError(
            "PPO checkpoint tactical trace episode is not the pending stream index"
        )

    session_before = sha256(_canonical_bytes(session.serialize())).hexdigest()
    environment = environment_factory(stream_index)
    records: list[PPOTacticalEpisodeDecisionCost] = []
    _instrument_episode_engine(
        environment._backend._tactical_decision_engine,
        clock,
        records,
    )
    started = clock()
    episode = episode_collector(
        environment,
        training_run,
        episode_index=episode_index,
        policy=model.infer,
    )
    total = _elapsed(started, clock(), "PPO checkpoint tactical trace")

    if model.parameter_sha256 != policy_sha256:
        raise PPOContractError("PPO checkpoint tactical trace policy changed")
    session_after = sha256(_canonical_bytes(session.serialize())).hexdigest()
    if session_after != session_before:
        raise PPOContractError("PPO checkpoint tactical trace mutated campaign state")
    if (
        episode.training_run != training_run
        or episode.episode_index != episode_index
        or episode.game_seed != training_run.game_seed(episode_index)
        or episode.truncated
        or not episode.status.terminal
    ):
        raise PPOContractError("PPO checkpoint tactical trace episode provenance drifted")

    frozen_records = tuple(records)
    tactical = _validate_decision_timings(frozen_records)
    if tactical > total and not math.isclose(tactical, total, abs_tol=1e-9):
        raise PPOContractError(
            "PPO checkpoint tactical trace exceeds complete episode timing"
        )
    episode_sha256 = sha256(episode.to_json().encode("utf-8")).hexdigest()
    return PPOCheckpointTacticalEpisodeReport(
        schema=PPO_CHECKPOINT_TACTICAL_EPISODE_SCHEMA,
        campaign_version=PPO_CAMPAIGN_VERSION,
        checkpoint_sha256=checkpoint_sha256,
        training_run_sha256=training_run.sha256,
        policy_parameter_sha256=policy_sha256,
        session_sha256_before=session_before,
        session_sha256_after=session_after,
        root_seed=root_seed,
        episode_index=episode_index,
        stream_index=stream_index,
        game_seed=episode.game_seed,
        episode_sha256=episode_sha256,
        terminal_status=episode.status.value,
        environment_transitions=episode.action_count,
        total_elapsed_seconds=total,
        tactical_elapsed_seconds=tactical,
        committed=False,
        decisions=frozen_records,
    )


def write_checkpoint_tactical_episode_report(
    path: str | Path,
    report: PPOCheckpointTacticalEpisodeReport,
) -> str:
    """Atomically publish one canonical checkpoint tactical trace."""
    if not isinstance(report, PPOCheckpointTacticalEpisodeReport):
        raise TypeError("report must be PPOCheckpointTacticalEpisodeReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError(
            "PPO checkpoint tactical report directory does not exist"
        )
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--episode-index", required=True, type=int)
    parser.add_argument("--output-path", required=True)
    arguments = parser.parse_args(argv)
    report = trace_checkpoint_ppo_episode_tactical_costs(
        arguments.root_seed,
        arguments.checkpoint_path,
        episode_index=arguments.episode_index,
    )
    report_sha256 = write_checkpoint_tactical_episode_report(
        arguments.output_path,
        report,
    )
    print(
        json.dumps(
            {
                "schema": report.schema,
                "output_path": str(Path(arguments.output_path)),
                "report_sha256": report_sha256,
                "checkpoint_sha256": report.checkpoint_sha256,
                "policy_parameter_sha256": report.policy_parameter_sha256,
                "episode_index": report.episode_index,
                "stream_index": report.stream_index,
                "episode_sha256": report.episode_sha256,
                "decision_count": len(report.decisions),
                "total_elapsed_seconds": report.total_elapsed_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
