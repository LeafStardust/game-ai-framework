"""Read-only timing attribution for one exact restored PPO campaign wave."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import multiprocessing
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
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_initial_batch_timing import (
    PPOEpisodeTiming,
    _collect_timed_production_wave,
    _elapsed,
    _require_timed_wave,
)
from games.balatro.env.ppo_training_session import PPOEpisodeRequest


PPO_CAMPAIGN_WAVE_TIMING_SCHEMA = "balatro-red-white-ppo-campaign-wave-timing-v1"


@dataclass(frozen=True)
class PPOCampaignWaveTimingReport:
    schema: str
    campaign_version: str
    checkpoint_sha256: str
    training_run_sha256: str
    policy_parameter_sha256: str
    maximum_workers: int
    elapsed_seconds: float
    requested_episode_indices: tuple[int, ...]
    requested_stream_indices: tuple[int, ...]
    episodes: tuple[PPOEpisodeTiming, ...]

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def _read_canonical_checkpoint(path: Path) -> tuple[bytes, object]:
    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError("PPO timing checkpoint is unreadable") from error
    if _canonical_bytes(payload) != content:
        raise PPOContractError("PPO timing checkpoint is not canonical JSON")
    return content, payload


def measure_checkpoint_wave_timing(
    root_seed: str | int,
    checkpoint_path: str | Path,
    *,
    maximum_workers: int,
    clock: Callable[[], float] = perf_counter,
    episode_wave_collector=None,
) -> PPOCampaignWaveTimingReport:
    """Time one complete ordered wave without advancing restored campaign state."""
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("PPO timing maximum workers must be from 1 through 8")
    if not callable(clock):
        raise TypeError("clock must be callable")
    if episode_wave_collector is not None and not callable(episode_wave_collector):
        raise TypeError("episode_wave_collector must be callable")

    path = Path(checkpoint_path)
    checkpoint_bytes, payload = _read_canonical_checkpoint(path)
    checkpoint_sha256 = sha256(checkpoint_bytes).hexdigest()
    training_run = PPOTrainingRun.from_seed(root_seed)
    session = _restore_session(training_run, payload, make_ppo_training_environment)
    learner = session.learner
    model = learner.model
    policy_sha256 = model.parameter_sha256
    indices = learner.assembler.next_episode_indices
    if len(indices) != 8:
        raise PPOContractError("PPO timing checkpoint does not own eight stream indices")
    requests = tuple(
        PPOEpisodeRequest(stream_index, episode_index)
        for stream_index, episode_index in enumerate(indices)
    )
    if any(request.episode_index % 8 != request.stream_index for request in requests):
        raise PPOContractError("PPO timing checkpoint stream ordering drifted")

    session_before = sha256(_canonical_bytes(session.serialize())).hexdigest()
    started = clock()
    if episode_wave_collector is not None:
        timed = episode_wave_collector(requests, training_run, model)
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers, mp_context=context
        ) as executor:
            timed = _collect_timed_production_wave(
                executor,
                requests,
                training_run,
                model,
            )
    elapsed = _elapsed(started, clock(), "PPO campaign wave timing")
    timed = _require_timed_wave(timed, requests, policy_sha256=policy_sha256)
    if model.parameter_sha256 != policy_sha256:
        raise PPOContractError("PPO timing policy changed during collection")
    session_after = sha256(_canonical_bytes(session.serialize())).hexdigest()
    if session_after != session_before:
        raise PPOContractError("PPO timing mutated restored campaign state")

    episodes = tuple(
        PPOEpisodeTiming(
            episode_index=value.collected.episode.episode_index,
            stream_index=value.collected.request.stream_index,
            game_seed=value.collected.episode.game_seed,
            action_count=value.collected.episode.action_count,
            terminal_status=value.collected.episode.status.value,
            episode_sha256=sha256(
                value.collected.episode.to_json().encode("utf-8")
            ).hexdigest(),
            policy_parameter_sha256=value.collected.policy_parameter_sha256,
            elapsed_seconds=float(value.elapsed_seconds),
            committed=False,
        )
        for value in timed
    )
    return PPOCampaignWaveTimingReport(
        schema=PPO_CAMPAIGN_WAVE_TIMING_SCHEMA,
        campaign_version=PPO_CAMPAIGN_VERSION,
        checkpoint_sha256=checkpoint_sha256,
        training_run_sha256=training_run.sha256,
        policy_parameter_sha256=policy_sha256,
        maximum_workers=maximum_workers,
        elapsed_seconds=elapsed,
        requested_episode_indices=tuple(request.episode_index for request in requests),
        requested_stream_indices=tuple(request.stream_index for request in requests),
        episodes=episodes,
    )


def write_campaign_wave_timing_report(
    path: str | Path,
    report: PPOCampaignWaveTimingReport,
) -> str:
    """Atomically publish one canonical complete-wave timing report."""
    if not isinstance(report, PPOCampaignWaveTimingReport):
        raise TypeError("report must be PPOCampaignWaveTimingReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError("PPO timing report directory does not exist")
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--maximum-workers", required=True, type=int)
    parser.add_argument("--output-path", required=True)
    arguments = parser.parse_args(argv)
    report = measure_checkpoint_wave_timing(
        arguments.root_seed,
        arguments.checkpoint_path,
        maximum_workers=arguments.maximum_workers,
    )
    report_sha256 = write_campaign_wave_timing_report(
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
                "requested_episode_indices": report.requested_episode_indices,
                "elapsed_seconds": report.elapsed_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
