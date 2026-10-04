"""Production artifact and CLI owner for the frozen Red/White PPO campaign."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
from typing import Any, Callable

from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.ppo_training_session import (
    PPO_TRAINING_SESSION_VERSION,
    PPOCollectedEpisode,
    PPOEpisodeRequest,
    PPOTrainingSession,
)
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_SELECTIVE,
    LiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


PPO_CAMPAIGN_VERSION = "balatro-red-white-ppo-campaign-v7"
PPO_TACTICAL_FACTORY_VERSION = "balatro-red-white-ppo-tactical-factory-v2"
PPO_PARALLEL_COLLECTION_VERSION = "balatro-red-white-ppo-parallel-collection-v6"
PPO_CAMPAIGN_PROGRESS_VERSION = "balatro-red-white-ppo-progress-v7"
PPO_CAMPAIGN_FINAL_VERSION = "balatro-red-white-ppo-final-v7"
CHECKPOINT_NAME = "checkpoint.json"
PROGRESS_NAME = "progress.json"
FINAL_NAME = "final.json"


def make_ppo_training_environment(stream_index: int) -> BalatroHeadlessEnvironment:
    """Construct one stream with the frozen production tactical authority."""
    if (
        isinstance(stream_index, bool)
        or not isinstance(stream_index, int)
        or not 0 <= stream_index < 8
    ):
        raise PPOContractError("PPO environment stream index is invalid")
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=4,
        child_play_width=4,
        child_discard_width=2,
        horizon=2,
        max_nodes=3000,
    )
    policy = StrategyAwareLiveHandActionPolicy(evaluator=planner.evaluator)
    engine = LiveHandActionDecisionEngine(
        planner=planner,
        policy=policy,
        max_horizon=8,
        max_search_nodes=5000,
        exact_limit=128,
        child_exact_limit=8,
        search_schedule_mode=SEARCH_SCHEDULE_SELECTIVE,
        max_search_seconds=None,
    )
    return BalatroHeadlessEnvironment(PPOHeadlessBackend(engine))


def _collect_production_episode(
    request: PPOEpisodeRequest, training_run: PPOTrainingRun, model
) -> PPOCollectedEpisode:
    if not isinstance(request, PPOEpisodeRequest):
        raise TypeError("request must be PPOEpisodeRequest")
    policy_sha256 = getattr(model, "parameter_sha256", None)
    environment = make_ppo_training_environment(request.stream_index)
    episode = collect_complete_ppo_episode(
        environment,
        training_run,
        episode_index=request.episode_index,
        policy=model.infer,
    )
    if getattr(model, "parameter_sha256", None) != policy_sha256:
        raise PPOContractError("PPO worker policy changed during episode collection")
    return PPOCollectedEpisode(request, policy_sha256, episode)


def _collect_production_wave(
    executor: ProcessPoolExecutor,
    requests: tuple[PPOEpisodeRequest, ...],
    training_run: PPOTrainingRun,
    model,
) -> tuple[PPOCollectedEpisode, ...]:
    futures = tuple(
        executor.submit(_collect_production_episode, request, training_run, model)
        for request in requests
    )
    return tuple(future.result() for future in futures)


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOContractError("PPO campaign artifact is not canonical JSON") from error


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError(f"PPO campaign artifact is unreadable: {path.name}") from error


def _checkpoint_payload(run: PPOTrainingRun, session: PPOTrainingSession) -> dict[str, Any]:
    return {
        "version": PPO_CAMPAIGN_VERSION,
        "tactical_factory_version": PPO_TACTICAL_FACTORY_VERSION,
        "parallel_collection_version": PPO_PARALLEL_COLLECTION_VERSION,
        "training_run": run.as_dict(),
        "session": session.serialize(),
    }


def _restore_session(
    run: PPOTrainingRun,
    payload: object,
    environment_factory,
) -> PPOTrainingSession:
    fields = {
        "version",
        "tactical_factory_version",
        "parallel_collection_version",
        "training_run",
        "session",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise PPOContractError("PPO campaign checkpoint fields are incomplete")
    if payload["version"] != PPO_CAMPAIGN_VERSION:
        raise PPOContractError("PPO campaign version mismatch")
    if payload["tactical_factory_version"] != PPO_TACTICAL_FACTORY_VERSION:
        raise PPOContractError("PPO campaign tactical factory version mismatch")
    if payload["parallel_collection_version"] != PPO_PARALLEL_COLLECTION_VERSION:
        raise PPOContractError("PPO campaign parallel collection version mismatch")
    if payload["training_run"] != run.as_dict():
        raise PPOContractError("PPO campaign training-run provenance mismatch")
    return PPOTrainingSession.restore(run, environment_factory, payload["session"])


def _state_manifest(
    run: PPOTrainingRun,
    session: PPOTrainingSession,
    checkpoint_sha256: str,
) -> dict[str, Any]:
    return {
        "version": PPO_CAMPAIGN_PROGRESS_VERSION,
        "campaign_version": PPO_CAMPAIGN_VERSION,
        "tactical_factory_version": PPO_TACTICAL_FACTORY_VERSION,
        "parallel_collection_version": PPO_PARALLEL_COLLECTION_VERSION,
        "session_version": PPO_TRAINING_SESSION_VERSION,
        "training_run_sha256": run.sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "completed_batch_count": session.learner.completed_batch_count,
        "optimizer_consumed_transitions": session.optimizer_consumed_transitions,
        "collected_environment_transitions": (
            session.learner.total_consumed_environment_transitions
        ),
        "next_episode_indices": list(session.learner.assembler.next_episode_indices),
        "complete": session.complete,
    }


def run_ppo_campaign(
    root_seed: str | int,
    artifact_directory: str | Path,
    *,
    maximum_episodes: int,
    maximum_batches: int,
    maximum_workers: int,
    environment_factory=make_ppo_training_environment,
    session_opener: Callable[[PPOTrainingRun, object | None, object], PPOTrainingSession]
    | None = None,
    episode_wave_collector=None,
) -> dict[str, Any]:
    if isinstance(maximum_episodes, bool) or not isinstance(maximum_episodes, int):
        raise PPOContractError("PPO campaign maximum episodes must be an exact integer")
    if maximum_episodes <= 0:
        raise PPOContractError("PPO campaign maximum episodes must be positive")
    if isinstance(maximum_batches, bool) or not isinstance(maximum_batches, int):
        raise PPOContractError("PPO campaign maximum batches must be an exact integer")
    target_batch_count = (
        PPO_TRAINING_CONTRACT.total_environment_steps
        // PPO_TRAINING_CONTRACT.rollout_batch_size
    )
    if maximum_batches <= 0 or maximum_batches > target_batch_count:
        raise PPOContractError(
            "PPO campaign maximum batches must fit the frozen schedule"
        )
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("PPO campaign maximum workers must be from 1 through 8")
    if episode_wave_collector is not None and not callable(episode_wave_collector):
        raise TypeError("episode_wave_collector must be callable")
    directory = Path(artifact_directory)
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint_path = directory / CHECKPOINT_NAME
    progress_path = directory / PROGRESS_NAME
    final_path = directory / FINAL_NAME
    run = PPOTrainingRun.from_seed(root_seed)
    existing = _read_json(checkpoint_path) if checkpoint_path.exists() else None
    if existing is None and (progress_path.exists() or final_path.exists()):
        raise PPOContractError("PPO campaign directory has artifacts without a checkpoint")

    if session_opener is None:
        session = (
            PPOTrainingSession(run, environment_factory)
            if existing is None
            else _restore_session(run, existing, environment_factory)
        )
    else:
        session = session_opener(run, existing, environment_factory)
    if final_path.exists() and not session.complete:
        raise PPOContractError(
            "PPO campaign final artifact contradicts an incomplete checkpoint"
        )

    def publish_committed(current_session, _episode):
        checkpoint_bytes = _canonical_bytes(_checkpoint_payload(run, current_session))
        _atomic_write(checkpoint_path, checkpoint_bytes)
        progress = _state_manifest(
            run, current_session, sha256(checkpoint_bytes).hexdigest()
        )
        _atomic_write(progress_path, _canonical_bytes(progress))

    if episode_wave_collector is not None:
        session.advance_parallel(
            maximum_episodes=maximum_episodes,
            maximum_batches=maximum_batches,
            wave_collector=episode_wave_collector,
            on_episode_committed=publish_committed,
        )
    else:
        if environment_factory is not make_ppo_training_environment:
            raise PPOContractError(
                "custom PPO campaign environments require an explicit wave collector"
            )
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers, mp_context=context
        ) as executor:
            session.advance_parallel(
                maximum_episodes=maximum_episodes,
                maximum_batches=maximum_batches,
                wave_collector=lambda requests, training_run, model: (
                    _collect_production_wave(
                        executor, requests, training_run, model
                    )
                ),
                on_episode_committed=publish_committed,
            )

    if not checkpoint_path.exists():
        checkpoint_bytes = _canonical_bytes(_checkpoint_payload(run, session))
        _atomic_write(checkpoint_path, checkpoint_bytes)
    else:
        try:
            checkpoint_bytes = checkpoint_path.read_bytes()
        except OSError as error:
            raise PPOContractError("PPO campaign checkpoint is unreadable") from error
    progress = _state_manifest(run, session, sha256(checkpoint_bytes).hexdigest())
    _atomic_write(progress_path, _canonical_bytes(progress))

    if session.complete:
        final = {
            **progress,
            "version": PPO_CAMPAIGN_FINAL_VERSION,
            "parameter_sha256": session.learner.model.parameter_sha256,
        }
        _atomic_write(final_path, _canonical_bytes(final))
        return final
    return progress


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--maximum-episodes", required=True, type=int)
    parser.add_argument("--maximum-batches", required=True, type=int)
    parser.add_argument("--maximum-workers", required=True, type=int)
    arguments = parser.parse_args(argv)
    progress = run_ppo_campaign(
        arguments.root_seed,
        arguments.artifact_directory,
        maximum_episodes=arguments.maximum_episodes,
        maximum_batches=arguments.maximum_batches,
        maximum_workers=arguments.maximum_workers,
    )
    print(json.dumps(progress, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
