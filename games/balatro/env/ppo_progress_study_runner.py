"""Resumable eight-batch learning-curve study for the progress reward."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from games.balatro.env.ppo_campaign import (
    CHECKPOINT_NAME,
    FINAL_NAME,
    PROGRESS_NAME,
    PPO_PROGRESS_STUDY_BATCH_LIMIT,
    _atomic_write,
    _canonical_bytes,
    _reconcile_progress_artifact,
    _restore_session,
    make_ppo_progress_training_environment,
    run_ppo_campaign,
)
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_REWARD_CONTRACT,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_progress_study import (
    STUDY_JOURNAL_NAME,
    STUDY_MILESTONE_BATCHES,
    STUDY_MILESTONE_DIRECTORY,
    STUDY_MILESTONE_MANIFEST_NAME,
    PPOProgressStudyEpisodeRecord,
    PPOProgressStudyJournal,
    load_progress_study_journal,
    load_progress_study_milestone,
    publish_progress_study_milestone,
    write_progress_study_journal,
)
from games.balatro.env.ppo_progress_study_evaluation import (
    STUDY_EVALUATION_NAME,
    load_progress_study_evaluation,
    run_progress_study_evaluation,
)
from games.balatro.env.ppo_training_session import PPOTrainingSession


PPO_PROGRESS_STUDY_ROOT_SEED = "RED-WHITE-PROGRESS-STUDY-V1"
PPO_PROGRESS_STUDY_IDENTITY_SCHEMA = "balatro-red-white-progress-study-v1"
PPO_PROGRESS_STUDY_RUNTIME_SCHEMA = "balatro-red-white-progress-study-runtime-v1"
PPO_PROGRESS_STUDY_REPORT_SCHEMA = "balatro-red-white-progress-study-report-v1"
STUDY_IDENTITY_NAME = "progress_study_identity.json"
STUDY_RUNTIME_NAME = "progress_study_runtime.json"
STUDY_REPORT_NAME = "progress_study_report.json"


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOContractError(f"PPO progress study {label} is invalid")
    return value


def _read_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError(f"PPO progress study {label} is unreadable") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise PPOContractError(f"PPO progress study {label} is noncanonical")
    return value, raw


@dataclass(frozen=True)
class PPOProgressStudyIdentity:
    schema: str
    root_seed: str
    training_run_sha256: str
    training_contract_sha256: str
    reward_contract: str
    batch_limit: int
    milestone_batches: tuple[int, ...]
    initial_policy_parameter_sha256: str

    def __post_init__(self) -> None:
        if (
            self.schema != PPO_PROGRESS_STUDY_IDENTITY_SCHEMA
            or self.root_seed != PPO_PROGRESS_STUDY_ROOT_SEED
            or self.training_contract_sha256
            != PPO_PROGRESS_TRAINING_CONTRACT.sha256
            or self.reward_contract != PPO_PROGRESS_REWARD_CONTRACT
            or self.batch_limit != PPO_PROGRESS_STUDY_BATCH_LIMIT
            or self.milestone_batches != STUDY_MILESTONE_BATCHES
        ):
            raise PPOContractError("PPO progress study identity drifted")
        _digest(self.training_run_sha256, "identity training run")
        _digest(self.initial_policy_parameter_sha256, "identity initial policy")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["milestone_batches"] = list(self.milestone_batches)
        return value

    def to_json(self) -> str:
        return _canonical_bytes(self.as_dict()).decode("utf-8")


@dataclass(frozen=True)
class PPOProgressStudyRuntimeCall:
    completed_batch_count_before: int
    completed_batch_count_after: int
    committed_episode_count_before: int
    committed_episode_count_after: int
    elapsed_seconds: float

    def __post_init__(self) -> None:
        values = (
            self.completed_batch_count_before,
            self.completed_batch_count_after,
            self.committed_episode_count_before,
            self.committed_episode_count_after,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise PPOContractError("PPO progress study runtime counter is invalid")
        if (
            not 0 <= self.completed_batch_count_before <= self.completed_batch_count_after <= 8
            or self.completed_batch_count_after - self.completed_batch_count_before > 1
            or not 0 <= self.committed_episode_count_before
            < self.committed_episode_count_after
        ):
            raise PPOContractError("PPO progress study runtime counters drifted")
        if (
            isinstance(self.elapsed_seconds, bool)
            or not isinstance(self.elapsed_seconds, (int, float))
            or not math.isfinite(float(self.elapsed_seconds))
            or self.elapsed_seconds < 0.0
        ):
            raise PPOContractError("PPO progress study runtime sample is invalid")


@dataclass(frozen=True)
class PPOProgressStudyRuntime:
    schema: str
    training_run_sha256: str
    calls: tuple[PPOProgressStudyRuntimeCall, ...] = ()

    def __post_init__(self) -> None:
        if self.schema != PPO_PROGRESS_STUDY_RUNTIME_SCHEMA:
            raise PPOContractError("PPO progress study runtime schema mismatch")
        _digest(self.training_run_sha256, "runtime training run")
        if not isinstance(self.calls, tuple) or any(
            not isinstance(call, PPOProgressStudyRuntimeCall) for call in self.calls
        ):
            raise PPOContractError("PPO progress study runtime calls are invalid")
        for prior, current in zip(self.calls, self.calls[1:]):
            if (
                not prior.completed_batch_count_after
                <= current.completed_batch_count_before
                <= prior.completed_batch_count_after + 1
                or current.committed_episode_count_before
                < prior.committed_episode_count_after
            ):
                raise PPOContractError("PPO progress study runtime order drifted")

    def append(self, call: PPOProgressStudyRuntimeCall) -> "PPOProgressStudyRuntime":
        return PPOProgressStudyRuntime(
            self.schema, self.training_run_sha256, self.calls + (call,)
        )

    def to_json(self) -> str:
        return _canonical_bytes(
            {
                "schema": self.schema,
                "training_run_sha256": self.training_run_sha256,
                "calls": [asdict(call) for call in self.calls],
            }
        ).decode("utf-8")

    def elapsed_through_batch(self, batch_count: int) -> float:
        if batch_count == 0:
            return 0.0
        elapsed = 0.0
        for call in self.calls:
            if call.completed_batch_count_before >= batch_count:
                return elapsed
            elapsed += call.elapsed_seconds
            if call.completed_batch_count_after >= batch_count:
                return elapsed
        return elapsed


def _load_runtime(path: Path, run: PPOTrainingRun) -> PPOProgressStudyRuntime:
    if not path.exists():
        return PPOProgressStudyRuntime(PPO_PROGRESS_STUDY_RUNTIME_SCHEMA, run.sha256)
    value, raw = _read_canonical(path, "runtime")
    try:
        runtime = PPOProgressStudyRuntime(
            value["schema"],
            value["training_run_sha256"],
            tuple(PPOProgressStudyRuntimeCall(**call) for call in value["calls"]),
        )
    except (KeyError, TypeError, PPOContractError) as error:
        raise PPOContractError("PPO progress study runtime is malformed") from error
    if runtime.training_run_sha256 != run.sha256 or runtime.to_json().encode() != raw:
        raise PPOContractError("PPO progress study runtime provenance drifted")
    return runtime


def _load_live_session(
    directory: Path, run: PPOTrainingRun
) -> tuple[PPOTrainingSession, PPOProgressStudyJournal]:
    checkpoint_path = directory / CHECKPOINT_NAME
    progress_path = directory / PROGRESS_NAME
    if checkpoint_path.exists():
        checkpoint, checkpoint_raw = _read_canonical(checkpoint_path, "checkpoint")
        session = _restore_session(
            run, checkpoint, make_ppo_progress_training_environment
        )
        _reconcile_progress_artifact(run, session, checkpoint_raw, progress_path)
    else:
        if progress_path.exists() or (directory / FINAL_NAME).exists():
            raise PPOContractError("PPO progress study has artifacts without checkpoint")
        session = PPOTrainingSession(run, make_ppo_progress_training_environment)
    journal_path = directory / STUDY_JOURNAL_NAME
    journal = load_progress_study_journal(journal_path, run)
    reconciled = journal.reconciled(session.learner.assembler.next_episode_indices)
    if reconciled != journal:
        write_progress_study_journal(journal_path, reconciled)
        journal = reconciled
    return session, journal


def initialize_progress_study(
    artifact_directory: str | Path,
) -> tuple[PPOTrainingRun, PPOProgressStudyIdentity]:
    directory = Path(artifact_directory)
    identity_path = directory / STUDY_IDENTITY_NAME
    run = PPOTrainingRun.from_seed(
        PPO_PROGRESS_STUDY_ROOT_SEED, contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    expected = PPOProgressStudyIdentity(
        PPO_PROGRESS_STUDY_IDENTITY_SCHEMA,
        PPO_PROGRESS_STUDY_ROOT_SEED,
        run.sha256,
        PPO_PROGRESS_TRAINING_CONTRACT.sha256,
        PPO_PROGRESS_REWARD_CONTRACT,
        PPO_PROGRESS_STUDY_BATCH_LIMIT,
        STUDY_MILESTONE_BATCHES,
        PPOActorCritic(run).parameter_sha256,
    )
    if identity_path.exists():
        value, raw = _read_canonical(identity_path, "identity")
        try:
            restored = PPOProgressStudyIdentity(
                **{**value, "milestone_batches": tuple(value["milestone_batches"])}
            )
        except (KeyError, TypeError, PPOContractError) as error:
            raise PPOContractError("PPO progress study identity is malformed") from error
        if restored != expected or restored.to_json().encode() != raw:
            raise PPOContractError("PPO progress study identity provenance drifted")
        load_progress_study_milestone(directory, run, 0)
        return run, restored
    if directory.exists():
        if not directory.is_dir():
            raise PPOContractError("PPO progress study artifact path is not a directory")
        if any(directory.iterdir()):
            raise PPOContractError("PPO progress study requires a fresh empty directory")
    else:
        directory.mkdir(parents=True)
    session = PPOTrainingSession(run, make_ppo_progress_training_environment)
    journal = PPOProgressStudyJournal.fresh(run)
    write_progress_study_journal(directory / STUDY_JOURNAL_NAME, journal)
    publish_progress_study_milestone(directory, session, journal, 0)
    _atomic_write(identity_path, expected.to_json().encode("utf-8"))
    return run, expected


def _summary(values: tuple[float, ...], label: str) -> dict[str, float | int]:
    if not values or any(not math.isfinite(value) for value in values):
        raise PPOContractError(f"PPO progress study {label} samples are invalid")
    mean = math.fsum(values) / len(values)
    return {
        "count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": mean,
        "variance": math.fsum((value - mean) ** 2 for value in values) / len(values),
    }


def _build_report(
    directory: Path,
    run: PPOTrainingRun,
    identity: PPOProgressStudyIdentity,
    runtime: PPOProgressStudyRuntime,
) -> dict[str, Any]:
    identity_raw = (directory / STUDY_IDENTITY_NAME).read_bytes()
    checkpoints = []
    for batch_count in STUDY_MILESTONE_BATCHES:
        milestone = load_progress_study_milestone(directory, run, batch_count)
        evaluation = load_progress_study_evaluation(directory, run, batch_count)
        records = milestone.journal.records
        rewards = tuple(value for record in records for value in record.rewards)
        advantages = tuple(value for record in records for value in record.advantages)
        depths = tuple(float(record.action_count) for record in records)
        statuses = Counter(record.status for record in records)
        evaluation_path = (
            directory
            / STUDY_MILESTONE_DIRECTORY
            / f"batch-{batch_count:03d}"
            / STUDY_EVALUATION_NAME
        )
        checkpoints.append(
            {
                **milestone.milestone.as_dict(),
                "milestone_manifest_sha256": sha256(
                    evaluation_path.with_name(STUDY_MILESTONE_MANIFEST_NAME).read_bytes()
                ).hexdigest(),
                "evaluation_sha256": sha256(evaluation_path.read_bytes()).hexdigest(),
                "evaluation_summary": evaluation.as_dict()["summary"],
                "committed_episode_count": len(records),
                "terminal_status_counts": dict(sorted(statuses.items())),
                "reward_statistics": None if not rewards else _summary(rewards, "reward"),
                "advantage_statistics": (
                    None if not advantages else _summary(advantages, "advantage")
                ),
                "episode_depth_statistics": (
                    None if not depths else _summary(depths, "episode depth")
                ),
                "measured_training_seconds": runtime.elapsed_through_batch(batch_count),
                "fail_closed_counts": {
                    "campaign_abort_count": 0,
                    "nonfinite_advantage_count": 0,
                    "nonfinite_reward_count": 0,
                    "reward_contract_mismatch_count": 0,
                    "truncated_episode_count": 0,
                    "unsupported_mechanic_count": 0,
                },
            }
        )
    unmeasured_episodes = 0
    prior_episode_count = 0
    for call in runtime.calls:
        unmeasured_episodes += call.committed_episode_count_before - prior_episode_count
        prior_episode_count = call.committed_episode_count_after
    final_episodes = checkpoints[-1]["committed_episode_count"]
    unmeasured_episodes += final_episodes - prior_episode_count
    return {
        "schema": PPO_PROGRESS_STUDY_REPORT_SCHEMA,
        "training_run_sha256": run.sha256,
        "identity_sha256": sha256(identity_raw).hexdigest(),
        "training_contract_sha256": identity.training_contract_sha256,
        "reward_contract": identity.reward_contract,
        "batch_limit": identity.batch_limit,
        "complete": True,
        "measured_training_seconds": math.fsum(
            call.elapsed_seconds for call in runtime.calls
        ),
        "unmeasured_interrupted_episode_count": unmeasured_episodes,
        "checkpoints": checkpoints,
    }


def run_progress_study(
    artifact_directory: str | Path,
    *,
    maximum_episodes_per_call: int,
    maximum_workers: int,
    clock: Callable[[], float] = perf_counter,
    campaign_runner=run_ppo_campaign,
    evaluation_runner=run_progress_study_evaluation,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if (
        isinstance(maximum_episodes_per_call, bool)
        or not isinstance(maximum_episodes_per_call, int)
        or maximum_episodes_per_call < 1
    ):
        raise PPOContractError("PPO progress study maximum episodes is invalid")
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("PPO progress study workers must be from 1 through 8")
    if not callable(clock) or not callable(campaign_runner) or not callable(evaluation_runner):
        raise TypeError("PPO progress study runner dependency is not callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("PPO progress study callback is not callable")
    directory = Path(artifact_directory)
    run, identity = initialize_progress_study(directory)
    runtime_path = directory / STUDY_RUNTIME_NAME
    runtime = _load_runtime(runtime_path, run)

    def ensure_evaluation(batch_count: int) -> None:
        path = (
            directory
            / STUDY_MILESTONE_DIRECTORY
            / f"batch-{batch_count:03d}"
            / STUDY_EVALUATION_NAME
        )
        if path.exists():
            load_progress_study_evaluation(directory, run, batch_count)
        else:
            evaluation_runner(
                directory,
                run,
                batch_count,
                maximum_workers=maximum_workers,
                progress_callback=(
                    None
                    if progress_callback is None
                    else lambda completed, total: progress_callback(
                        {
                            "phase": "evaluation",
                            "batch": batch_count,
                            "completed_seed_pairs": completed,
                            "total_seed_pairs": total,
                        }
                    )
                ),
            )

    ensure_evaluation(0)
    session, journal = _load_live_session(directory, run)
    current_batch = session.learner.completed_batch_count
    for completed_milestone in STUDY_MILESTONE_BATCHES[1:]:
        if completed_milestone >= current_batch:
            break
        load_progress_study_milestone(directory, run, completed_milestone)
        ensure_evaluation(completed_milestone)
    if current_batch in STUDY_MILESTONE_BATCHES and current_batch != 0:
        publish_progress_study_milestone(
            directory, session, journal, current_batch
        )
        ensure_evaluation(current_batch)
    while session.learner.completed_batch_count < PPO_PROGRESS_STUDY_BATCH_LIMIT:
        before_batch = session.learner.completed_batch_count
        before_episodes = len(journal.records)
        current_journal = journal

        def observe(current_session, episode) -> None:
            nonlocal current_journal
            current_journal = current_journal.append(
                PPOProgressStudyEpisodeRecord.from_episode(current_session, episode)
            )
            write_progress_study_journal(
                directory / STUDY_JOURNAL_NAME, current_journal
            )

        started = clock()
        campaign_runner(
            PPO_PROGRESS_STUDY_ROOT_SEED,
            directory,
            maximum_episodes=maximum_episodes_per_call,
            maximum_batches=1,
            maximum_workers=maximum_workers,
            training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
            episode_commit_observer=observe,
            progress_study_batch_limit=PPO_PROGRESS_STUDY_BATCH_LIMIT,
        )
        elapsed = float(clock()) - float(started)
        if not math.isfinite(elapsed) or elapsed < 0.0:
            raise PPOContractError("PPO progress study clock moved backwards")
        session, journal = _load_live_session(directory, run)
        after_batch = session.learner.completed_batch_count
        after_episodes = len(journal.records)
        if after_batch not in {before_batch, before_batch + 1} or after_episodes <= before_episodes:
            raise PPOContractError("PPO progress study campaign made invalid progress")
        runtime = runtime.append(
            PPOProgressStudyRuntimeCall(
                before_batch,
                after_batch,
                before_episodes,
                after_episodes,
                elapsed,
            )
        )
        _atomic_write(runtime_path, runtime.to_json().encode("utf-8"))
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "training",
                    "completed_batch_count": after_batch,
                    "committed_episode_count": after_episodes,
                    "elapsed_seconds": elapsed,
                }
            )
        if after_batch in STUDY_MILESTONE_BATCHES and after_batch != before_batch:
            publish_progress_study_milestone(
                directory, session, journal, after_batch
            )
            ensure_evaluation(after_batch)

    report = _build_report(directory, run, identity, runtime)
    report_bytes = _canonical_bytes(report)
    report_path = directory / STUDY_REPORT_NAME
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise PPOContractError("PPO progress study final report is immutable")
    if not report_path.exists():
        _atomic_write(report_path, report_bytes)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--maximum-episodes-per-call", type=int, default=512)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(value: dict[str, Any]) -> None:
        print(_canonical_bytes(value).decode("utf-8"), flush=True)

    report = run_progress_study(
        arguments.artifact_directory,
        maximum_episodes_per_call=arguments.maximum_episodes_per_call,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.artifact_directory) / STUDY_REPORT_NAME
    print(
        _canonical_bytes(
            {
                "schema": report["schema"],
                "report_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
                "complete": report["complete"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
