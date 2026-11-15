"""Paired fixed-seed evaluation for the initial and one-batch progress policies."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import multiprocessing
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

from games.balatro.env.action_encoding import action_from_index, legal_action_mask
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.evaluation_diagnostics import (
    TerminalEpisodeMetrics,
    derive_terminal_episode_metrics,
)
from games.balatro.env.episode_backend import PPO_HEADLESS_BACKEND_SCHEMA
from games.balatro.env.ppo_campaign import (
    CHECKPOINT_NAME,
    PROGRESS_NAME,
    _atomic_write,
    _restore_session,
    make_ppo_progress_training_environment,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPO_REWARD_CONTRACT,
    PPOContractError,
    PPOPolicyOutput,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_progress_reward_pilot import PILOT_REPORT_NAME
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.env.state import RunStatus


PPO_PROGRESS_REWARD_EVALUATION_SCHEMA = (
    "balatro-red-white-progress-reward-paired-evaluation-v1"
)
PPO_PROGRESS_GREEDY_SELECTION_CONTRACT = (
    "balatro-red-white-masked-greedy-lowest-index-tiebreak-v1"
)
EVALUATION_REPORT_NAME = "progress_reward_paired_evaluation.json"


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOContractError("PPO progress evaluation is not canonical JSON") from error


def _read_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError(f"PPO progress {label} artifact is unreadable") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise PPOContractError(f"PPO progress {label} artifact is noncanonical")
    return value, raw


@dataclass(frozen=True)
class PPOProgressPolicyOutcome:
    status: str
    action_count: int
    metrics: TerminalEpisodeMetrics

    def __post_init__(self) -> None:
        if self.status not in {status.value for status in RunStatus if status.terminal}:
            raise PPOContractError("PPO progress evaluation status is invalid")
        if (
            isinstance(self.action_count, bool)
            or not isinstance(self.action_count, int)
            or self.action_count < 1
        ):
            raise PPOContractError("PPO progress evaluation action count is invalid")
        if not isinstance(self.metrics, TerminalEpisodeMetrics):
            raise PPOContractError("PPO progress evaluation metrics are invalid")
        if self.metrics.ante_8_cleared != (self.status == RunStatus.ANTE_8_WIN.value):
            raise PPOContractError("PPO progress evaluation status contradicts metrics")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action_count": self.action_count,
            "metrics": asdict(self.metrics),
        }


@dataclass(frozen=True)
class PPOProgressPairedEpisode:
    episode_index: int
    game_seed: str
    initial: PPOProgressPolicyOutcome
    one_batch: PPOProgressPolicyOutcome

    def __post_init__(self) -> None:
        if (
            isinstance(self.episode_index, bool)
            or not isinstance(self.episode_index, int)
            or not 0 <= self.episode_index < len(FIXED_SEEDED_EPISODES)
            or FIXED_SEEDED_EPISODES[self.episode_index].game_seed != self.game_seed
        ):
            raise PPOContractError("PPO progress paired episode provenance drifted")
        if not isinstance(self.initial, PPOProgressPolicyOutcome) or not isinstance(
            self.one_batch, PPOProgressPolicyOutcome
        ):
            raise PPOContractError("PPO progress paired episode outcome is invalid")

    def as_dict(self) -> dict[str, Any]:
        initial = self.initial.metrics
        trained = self.one_batch.metrics
        return {
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "initial": self.initial.as_dict(),
            "one_batch": self.one_batch.as_dict(),
            "deltas": {
                "ante_8_clear": int(trained.ante_8_cleared)
                - int(initial.ante_8_cleared),
                "ante_reached": trained.ante_reached - initial.ante_reached,
                "terminal_requirement_progress": (
                    trained.terminal_requirement_progress
                    - initial.terminal_requirement_progress
                ),
                "terminal_money": trained.terminal_money - initial.terminal_money,
                "action_count": self.one_batch.action_count - self.initial.action_count,
            },
        }


def _policy_summary(
    episodes: tuple[PPOProgressPairedEpisode, ...], attribute: str
) -> dict[str, float | int]:
    outcomes = tuple(getattr(episode, attribute) for episode in episodes)
    return {
        "episode_count": len(outcomes),
        "ante_8_clears": sum(outcome.metrics.ante_8_cleared for outcome in outcomes),
        "mean_ante_reached": fmean(
            outcome.metrics.ante_reached for outcome in outcomes
        ),
        "mean_terminal_requirement_progress": fmean(
            outcome.metrics.terminal_requirement_progress for outcome in outcomes
        ),
        "mean_terminal_money": fmean(
            outcome.metrics.terminal_money for outcome in outcomes
        ),
        "mean_action_count": fmean(outcome.action_count for outcome in outcomes),
    }


@dataclass(frozen=True)
class PPOProgressPairedEvaluationReport:
    schema: str
    fixed_corpus_sha256: str
    selection_contract: str
    training_run_sha256: str
    pilot_checkpoint_sha256: str
    pilot_progress_sha256: str
    pilot_report_sha256: str
    initial_policy_parameter_sha256: str
    one_batch_policy_parameter_sha256: str
    episodes: tuple[PPOProgressPairedEpisode, ...]

    def __post_init__(self) -> None:
        if self.schema != PPO_PROGRESS_REWARD_EVALUATION_SCHEMA:
            raise PPOContractError("PPO progress evaluation schema mismatch")
        if self.fixed_corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise PPOContractError("PPO progress evaluation corpus drifted")
        if self.selection_contract != PPO_PROGRESS_GREEDY_SELECTION_CONTRACT:
            raise PPOContractError("PPO progress evaluation selection contract drifted")
        for name in (
            "training_run_sha256",
            "pilot_checkpoint_sha256",
            "pilot_progress_sha256",
            "pilot_report_sha256",
            "initial_policy_parameter_sha256",
            "one_batch_policy_parameter_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or value != value.lower()
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise PPOContractError("PPO progress evaluation digest is invalid")
        expected = tuple(
            (spec.episode_index, spec.game_seed) for spec in FIXED_SEEDED_EPISODES
        )
        actual = tuple(
            (episode.episode_index, episode.game_seed)
            for episode in self.episodes
        ) if isinstance(self.episodes, tuple) else ()
        if actual != expected:
            raise PPOContractError(
                "PPO progress evaluation episodes are incomplete or out of order"
            )

    def as_dict(self) -> dict[str, Any]:
        initial = _policy_summary(self.episodes, "initial")
        one_batch = _policy_summary(self.episodes, "one_batch")
        return {
            "schema": self.schema,
            "fixed_corpus_sha256": self.fixed_corpus_sha256,
            "selection_contract": self.selection_contract,
            "training_run_sha256": self.training_run_sha256,
            "pilot_checkpoint_sha256": self.pilot_checkpoint_sha256,
            "pilot_progress_sha256": self.pilot_progress_sha256,
            "pilot_report_sha256": self.pilot_report_sha256,
            "initial_policy_parameter_sha256": (
                self.initial_policy_parameter_sha256
            ),
            "one_batch_policy_parameter_sha256": (
                self.one_batch_policy_parameter_sha256
            ),
            "summary": {
                "initial": initial,
                "one_batch": one_batch,
                "deltas": {
                    key: one_batch[key] - initial[key]
                    for key in initial
                    if key != "episode_count"
                },
            },
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return _canonical_bytes(self.as_dict()).decode("utf-8")


@dataclass(frozen=True)
class _LoadedPilotPolicies:
    training_run: PPOTrainingRun
    initial_model: PPOActorCritic
    one_batch_model: PPOActorCritic
    checkpoint_sha256: str
    progress_sha256: str
    report_sha256: str


def _load_pilot_policies(directory: Path) -> _LoadedPilotPolicies:
    checkpoint, checkpoint_raw = _read_canonical(
        directory / CHECKPOINT_NAME, "checkpoint"
    )
    progress, progress_raw = _read_canonical(directory / PROGRESS_NAME, "progress")
    pilot_report, pilot_report_raw = _read_canonical(
        directory / PILOT_REPORT_NAME, "report"
    )
    try:
        training_run = PPOTrainingRun(**checkpoint["training_run"])
    except (KeyError, TypeError, PPOContractError) as error:
        raise PPOContractError("PPO progress checkpoint training run is invalid") from error
    if training_run.contract_sha256 != PPO_PROGRESS_TRAINING_CONTRACT.sha256:
        raise PPOContractError("PPO progress checkpoint contract drifted")
    checkpoint_sha256 = sha256(checkpoint_raw).hexdigest()
    progress_sha256 = sha256(progress_raw).hexdigest()
    report_sha256 = sha256(pilot_report_raw).hexdigest()
    if (
        progress.get("checkpoint_sha256") != checkpoint_sha256
        or pilot_report.get("checkpoint_sha256") != checkpoint_sha256
        or pilot_report.get("progress_sha256") != progress_sha256
        or progress.get("training_run_sha256") != training_run.sha256
        or pilot_report.get("training_run_sha256") != training_run.sha256
        or pilot_report.get("completed_batch_count") != 1
        or pilot_report.get("optimizer_consumed_transitions")
        != PPO_PROGRESS_TRAINING_CONTRACT.rollout_batch_size
    ):
        raise PPOContractError("PPO progress pilot artifact linkage drifted")
    session = _restore_session(
        training_run, checkpoint, make_ppo_progress_training_environment
    )
    initial_model = PPOActorCritic(training_run)
    one_batch_model = session.learner.model
    if (
        session.learner.completed_batch_count != 1
        or initial_model.parameter_sha256
        != pilot_report.get("initial_policy_parameter_sha256")
        or one_batch_model.parameter_sha256
        != pilot_report.get("final_policy_parameter_sha256")
    ):
        raise PPOContractError("PPO progress pilot policy identity drifted")
    return _LoadedPilotPolicies(
        training_run,
        initial_model,
        one_batch_model,
        checkpoint_sha256,
        progress_sha256,
        report_sha256,
    )


def _evaluate_policy(
    model: PPOActorCritic,
    game_seed: str,
    environment: BalatroHeadlessEnvironment,
) -> PPOProgressPolicyOutcome:
    if not isinstance(model, PPOActorCritic):
        raise TypeError("PPO progress evaluation model must be PPOActorCritic")
    if not isinstance(environment, BalatroHeadlessEnvironment):
        raise TypeError("PPO progress evaluation environment is invalid")
    environment.reset(seed=game_seed)
    if (
        environment.frame.info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA
        or environment.frame.info.get("reward_contract") != PPO_REWARD_CONTRACT
    ):
        raise PPOContractError("PPO progress evaluation environment provenance drifted")
    frames = [deepcopy(environment.frame)]
    action_count = 0
    for _ in range(PPO_PROGRESS_TRAINING_CONTRACT.maximum_episode_actions):
        frame = environment.frame
        if frame.status.terminal:
            break
        legal_actions = environment.legal_actions()
        mask = legal_action_mask(legal_actions)
        output = model.infer(frame.encoded_observation(), mask)
        if not isinstance(output, PPOPolicyOutput):
            raise PPOContractError("PPO progress evaluation model output is invalid")
        allowed = tuple(index for index, value in enumerate(mask.values) if value)
        if not allowed or any(
            not math.isfinite(output.probabilities[index]) for index in allowed
        ):
            raise PPOContractError("PPO progress evaluation probabilities are invalid")
        action_index = min(
            allowed, key=lambda index: (-output.probabilities[index], index)
        )
        _, _, terminated, truncated, info = environment.step(
            action_from_index(action_index)
        )
        if truncated:
            raise PPOContractError("PPO progress evaluation episode truncated")
        if (
            info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA
            or info.get("reward_contract") != PPO_REWARD_CONTRACT
        ):
            raise PPOContractError("PPO progress evaluation environment drifted")
        action_count += 1
        frames.append(deepcopy(environment.frame))
        if terminated:
            break
    else:
        raise PPOContractError("PPO progress evaluation exceeded the action cap")
    if not environment.frame.status.terminal:
        raise PPOContractError("PPO progress evaluation episode is incomplete")
    metrics = derive_terminal_episode_metrics(
        status=environment.frame.status,
        action_count=action_count,
        frames=frames,
    )
    return PPOProgressPolicyOutcome(
        environment.frame.status.value, action_count, metrics
    )


def evaluate_policy_pair(
    spec: FixedSeededEpisodeSpec,
    initial_model: PPOActorCritic,
    one_batch_model: PPOActorCritic,
    *,
    environment_factory: Callable[[int], BalatroHeadlessEnvironment] = (
        make_ppo_training_environment
    ),
) -> PPOProgressPairedEpisode:
    if (
        not isinstance(spec, FixedSeededEpisodeSpec)
        or FIXED_SEEDED_EPISODES[spec.episode_index] != spec
    ):
        raise PPOContractError("PPO progress evaluation episode spec drifted")
    environment = environment_factory(spec.episode_index % 8)
    initial = _evaluate_policy(initial_model, spec.game_seed, environment)
    one_batch = _evaluate_policy(one_batch_model, spec.game_seed, environment)
    return PPOProgressPairedEpisode(
        spec.episode_index, spec.game_seed, initial, one_batch
    )


_WORKER_INITIAL_MODEL: PPOActorCritic | None = None
_WORKER_ONE_BATCH_MODEL: PPOActorCritic | None = None
_WORKER_ENVIRONMENT: BalatroHeadlessEnvironment | None = None


def _initialize_worker(
    initial_model: PPOActorCritic, one_batch_model: PPOActorCritic
) -> None:
    global _WORKER_INITIAL_MODEL, _WORKER_ONE_BATCH_MODEL, _WORKER_ENVIRONMENT
    _WORKER_INITIAL_MODEL = initial_model
    _WORKER_ONE_BATCH_MODEL = one_batch_model
    _WORKER_ENVIRONMENT = make_ppo_training_environment(0)


def _evaluate_worker(spec: FixedSeededEpisodeSpec) -> PPOProgressPairedEpisode:
    if (
        _WORKER_INITIAL_MODEL is None
        or _WORKER_ONE_BATCH_MODEL is None
        or _WORKER_ENVIRONMENT is None
    ):
        raise PPOContractError("PPO progress evaluation worker is uninitialized")
    initial = _evaluate_policy(
        _WORKER_INITIAL_MODEL, spec.game_seed, _WORKER_ENVIRONMENT
    )
    one_batch = _evaluate_policy(
        _WORKER_ONE_BATCH_MODEL, spec.game_seed, _WORKER_ENVIRONMENT
    )
    return PPOProgressPairedEpisode(
        spec.episode_index, spec.game_seed, initial, one_batch
    )


def run_progress_reward_evaluation(
    pilot_artifact_directory: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    pair_executor=None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> PPOProgressPairedEvaluationReport:
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("PPO progress evaluation workers must be from 1 through 8")
    destination = Path(output_path)
    if destination.exists():
        raise PPOContractError("PPO progress evaluation output already exists")
    if not destination.parent.is_dir():
        raise PPOContractError("PPO progress evaluation output directory is missing")
    policies = _load_pilot_policies(Path(pilot_artifact_directory))
    if pair_executor is not None and not callable(pair_executor):
        raise TypeError("PPO progress pair executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("PPO progress callback must be callable")
    episodes_values: list[PPOProgressPairedEpisode] = []

    def record(episode: PPOProgressPairedEpisode) -> None:
        episodes_values.append(episode)
        if progress_callback is not None:
            progress_callback(len(episodes_values), len(FIXED_SEEDED_EPISODES))

    if pair_executor is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(policies.initial_model, policies.one_batch_model),
        ) as executor:
            for episode in executor.map(_evaluate_worker, FIXED_SEEDED_EPISODES):
                record(episode)
    else:
        for spec in FIXED_SEEDED_EPISODES:
            record(
                pair_executor(spec, policies.initial_model, policies.one_batch_model)
            )
    episodes = tuple(episodes_values)
    report = PPOProgressPairedEvaluationReport(
        schema=PPO_PROGRESS_REWARD_EVALUATION_SCHEMA,
        fixed_corpus_sha256=FIXED_SEEDED_CORPUS_SHA256,
        selection_contract=PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
        training_run_sha256=policies.training_run.sha256,
        pilot_checkpoint_sha256=policies.checkpoint_sha256,
        pilot_progress_sha256=policies.progress_sha256,
        pilot_report_sha256=policies.report_sha256,
        initial_policy_parameter_sha256=policies.initial_model.parameter_sha256,
        one_batch_policy_parameter_sha256=policies.one_batch_model.parameter_sha256,
        episodes=episodes,
    )
    _atomic_write(destination, _canonical_bytes(report.as_dict()))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-artifact-directory", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)
    def report_progress(completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"completed_seed_pairs": completed, "total_seed_pairs": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_progress_reward_evaluation(
        arguments.pilot_artifact_directory,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=report_progress,
    )
    payload = report.as_dict()
    print(
        _canonical_bytes(
            {
                "schema": report.schema,
                "output_path": str(Path(arguments.output_path)),
                "report_sha256": sha256(report.to_json().encode("utf-8")).hexdigest(),
                "summary": payload["summary"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
