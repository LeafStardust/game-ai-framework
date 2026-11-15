"""Read-only policy-behavior attribution for progress-study milestones."""

from __future__ import annotations

import argparse
from collections import Counter
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

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    PUBLIC_ACTION_VERSION,
    action_from_index,
    legal_action_mask,
)
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.evaluation_diagnostics import (
    TerminalEpisodeMetrics,
    derive_terminal_episode_metrics,
)
from games.balatro.env.episode_backend import PPO_HEADLESS_BACKEND_SCHEMA
from games.balatro.env.ppo_campaign import (
    _atomic_write,
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
from games.balatro.env.ppo_progress_study import (
    STUDY_MILESTONE_BATCHES,
    STUDY_MILESTONE_DIRECTORY,
    STUDY_MILESTONE_MANIFEST_NAME,
    load_progress_study_milestone,
)
from games.balatro.env.ppo_progress_study_evaluation import (
    STUDY_EVALUATION_NAME,
    load_progress_study_evaluation,
)
from games.balatro.env.ppo_progress_study_runner import (
    initialize_progress_study,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.env.state import RunStatus


PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA = (
    "balatro-red-white-progress-study-behavior-attribution-v1"
)
STUDY_BEHAVIOR_REPORT_NAME = "policy_behavior_attribution.json"
ACTION_SCHEMA_SHA256 = sha256(
    json.dumps(
        [asdict(slot) for slot in PUBLIC_ACTION_SCHEMA.slots],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOContractError("PPO progress behavior report is not canonical") from error


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOContractError(f"PPO progress behavior {label} is invalid")
    return value


@dataclass(frozen=True)
class PPOProgressBehaviorDecision:
    decision_index: int
    observation_sha256: str
    legal_action_indices: tuple[int, ...]
    selected_action_index: int
    selected_probability: float
    legal_action_entropy: float
    value_estimate: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.decision_index, bool)
            or not isinstance(self.decision_index, int)
            or self.decision_index < 0
        ):
            raise PPOContractError("PPO progress behavior decision index is invalid")
        _digest(self.observation_sha256, "observation digest")
        if (
            not isinstance(self.legal_action_indices, tuple)
            or not self.legal_action_indices
            or tuple(sorted(set(self.legal_action_indices)))
            != self.legal_action_indices
            or any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(PUBLIC_ACTION_SCHEMA.slots)
                for index in self.legal_action_indices
            )
            or self.selected_action_index not in self.legal_action_indices
        ):
            raise PPOContractError("PPO progress behavior legal action set is invalid")
        for value in (
            self.selected_probability,
            self.legal_action_entropy,
            self.value_estimate,
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise PPOContractError("PPO progress behavior scalar is nonfinite")
        if not 0.0 <= self.selected_probability <= 1.0 or self.legal_action_entropy < 0.0:
            raise PPOContractError("PPO progress behavior probability statistic is invalid")

    def as_dict(self) -> dict[str, Any]:
        slot = PUBLIC_ACTION_SCHEMA.slots[self.selected_action_index]
        return {
            "decision_index": self.decision_index,
            "observation_sha256": self.observation_sha256,
            "legal_action_indices": list(self.legal_action_indices),
            "selected_action_index": self.selected_action_index,
            "selected_action_alias": slot.alias,
            "selected_action_params": dict(slot.params),
            "selected_probability": self.selected_probability,
            "legal_action_entropy": self.legal_action_entropy,
            "value_estimate": self.value_estimate,
        }


@dataclass(frozen=True)
class PPOProgressBehaviorEpisode:
    completed_batch_count: int
    episode_index: int
    game_seed: str
    status: str
    metrics: TerminalEpisodeMetrics
    decisions: tuple[PPOProgressBehaviorDecision, ...]
    terminal_deltas_from_batch_0: dict[str, float | int]

    def __post_init__(self) -> None:
        if self.completed_batch_count not in STUDY_MILESTONE_BATCHES:
            raise PPOContractError("PPO progress behavior batch is not staged")
        if (
            isinstance(self.episode_index, bool)
            or not isinstance(self.episode_index, int)
            or not 0 <= self.episode_index < len(FIXED_SEEDED_EPISODES)
            or FIXED_SEEDED_EPISODES[self.episode_index].game_seed != self.game_seed
        ):
            raise PPOContractError("PPO progress behavior episode provenance drifted")
        if self.status not in {status.value for status in RunStatus if status.terminal}:
            raise PPOContractError("PPO progress behavior status is invalid")
        if not isinstance(self.metrics, TerminalEpisodeMetrics):
            raise PPOContractError("PPO progress behavior terminal metrics are invalid")
        if (
            not isinstance(self.decisions, tuple)
            or not self.decisions
            or tuple(decision.decision_index for decision in self.decisions)
            != tuple(range(len(self.decisions)))
        ):
            raise PPOContractError("PPO progress behavior decisions are incomplete")
        expected_delta_keys = {
            "action_count",
            "ante_8_clear",
            "ante_reached",
            "terminal_money",
            "terminal_requirement_progress",
        }
        if set(self.terminal_deltas_from_batch_0) != expected_delta_keys:
            raise PPOContractError("PPO progress behavior terminal deltas drifted")

    def as_dict(self) -> dict[str, Any]:
        return {
            "completed_batch_count": self.completed_batch_count,
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "status": self.status,
            "metrics": asdict(self.metrics),
            "terminal_deltas_from_batch_0": self.terminal_deltas_from_batch_0,
            "decisions": [decision.as_dict() for decision in self.decisions],
        }


@dataclass(frozen=True)
class PPOProgressBehaviorMilestoneLink:
    completed_batch_count: int
    milestone_manifest_sha256: str
    evaluation_sha256: str
    policy_parameter_sha256: str

    def __post_init__(self) -> None:
        if self.completed_batch_count not in STUDY_MILESTONE_BATCHES:
            raise PPOContractError("PPO progress behavior milestone is not staged")
        for value in (
            self.milestone_manifest_sha256,
            self.evaluation_sha256,
            self.policy_parameter_sha256,
        ):
            _digest(value, "milestone digest")


def _slot_dict(index: int) -> dict[str, Any]:
    slot = PUBLIC_ACTION_SCHEMA.slots[index]
    return {"index": index, "alias": slot.alias, "params": dict(slot.params)}


def _checkpoint_summary(
    episodes: tuple[PPOProgressBehaviorEpisode, ...], batch_count: int
) -> dict[str, Any]:
    selected = [
        decision.selected_action_index
        for episode in episodes
        if episode.completed_batch_count == batch_count
        for decision in episode.decisions
    ]
    decisions = [
        decision
        for episode in episodes
        if episode.completed_batch_count == batch_count
        for decision in episode.decisions
    ]
    counts = Counter(selected)
    total = len(decisions)
    return {
        "completed_batch_count": batch_count,
        "episode_count": len(FIXED_SEEDED_EPISODES),
        "decision_count": total,
        "mean_selected_probability": fmean(
            decision.selected_probability for decision in decisions
        ),
        "mean_legal_action_entropy": fmean(
            decision.legal_action_entropy for decision in decisions
        ),
        "mean_value_estimate": fmean(decision.value_estimate for decision in decisions),
        "action_slots": [
            {
                **_slot_dict(index),
                "count": counts.get(index, 0),
                "frequency": counts.get(index, 0) / total,
            }
            for index in range(len(PUBLIC_ACTION_SCHEMA.slots))
        ],
    }


def _first_divergence(
    initial: PPOProgressBehaviorEpisode,
    candidate: PPOProgressBehaviorEpisode,
) -> dict[str, Any] | None:
    for initial_decision, candidate_decision in zip(
        initial.decisions, candidate.decisions, strict=False
    ):
        if initial_decision.selected_action_index == candidate_decision.selected_action_index:
            if initial_decision.observation_sha256 != candidate_decision.observation_sha256:
                raise PPOContractError("PPO progress behavior shared prefix drifted")
            continue
        if initial_decision.observation_sha256 != candidate_decision.observation_sha256:
            raise PPOContractError("PPO progress behavior divergence state drifted")
        return {
            "decision_index": initial_decision.decision_index,
            "observation_sha256": initial_decision.observation_sha256,
            "batch_0": {
                **_slot_dict(initial_decision.selected_action_index),
                "selected_probability": initial_decision.selected_probability,
                "legal_action_entropy": initial_decision.legal_action_entropy,
            },
            "candidate": {
                **_slot_dict(candidate_decision.selected_action_index),
                "selected_probability": candidate_decision.selected_probability,
                "legal_action_entropy": candidate_decision.legal_action_entropy,
            },
        }
    if len(initial.decisions) != len(candidate.decisions):
        raise PPOContractError("PPO progress behavior identical prefix length drifted")
    return None


@dataclass(frozen=True)
class PPOProgressBehaviorReport:
    schema: str
    training_run_sha256: str
    fixed_corpus_sha256: str
    action_schema_version: str
    action_schema_sha256: str
    milestone_links: tuple[PPOProgressBehaviorMilestoneLink, ...]
    episodes: tuple[PPOProgressBehaviorEpisode, ...]

    def __post_init__(self) -> None:
        if self.schema != PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA:
            raise PPOContractError("PPO progress behavior schema mismatch")
        _digest(self.training_run_sha256, "training run")
        if self.fixed_corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise PPOContractError("PPO progress behavior fixed corpus drifted")
        if (
            self.action_schema_version != PUBLIC_ACTION_VERSION
            or self.action_schema_sha256 != ACTION_SCHEMA_SHA256
        ):
            raise PPOContractError("PPO progress behavior action schema drifted")
        if tuple(link.completed_batch_count for link in self.milestone_links) != (
            STUDY_MILESTONE_BATCHES
        ):
            raise PPOContractError("PPO progress behavior milestone links are incomplete")
        expected = tuple(
            (batch, spec.episode_index, spec.game_seed)
            for batch in STUDY_MILESTONE_BATCHES
            for spec in FIXED_SEEDED_EPISODES
        )
        actual = tuple(
            (episode.completed_batch_count, episode.episode_index, episode.game_seed)
            for episode in self.episodes
        ) if isinstance(self.episodes, tuple) else ()
        if actual != expected:
            raise PPOContractError("PPO progress behavior episodes are incomplete")

    def as_dict(self) -> dict[str, Any]:
        by_key = {
            (episode.completed_batch_count, episode.episode_index): episode
            for episode in self.episodes
        }
        comparisons = []
        initial_episodes = {
            episode.episode_index: episode
            for episode in self.episodes
            if episode.completed_batch_count == 0
        }
        for batch in STUDY_MILESTONE_BATCHES[1:]:
            values = []
            transitions: Counter[str] = Counter()
            divergence_count = 0
            for spec in FIXED_SEEDED_EPISODES:
                initial = initial_episodes[spec.episode_index]
                candidate = by_key[(batch, spec.episode_index)]
                divergence = _first_divergence(initial, candidate)
                if divergence is not None:
                    divergence_count += 1
                    transition = (
                        f"{divergence['batch_0']['index']}->"
                        f"{divergence['candidate']['index']}"
                    )
                    transitions[transition] += 1
                values.append(
                    {
                        "episode_index": spec.episode_index,
                        "game_seed": spec.game_seed,
                        "first_greedy_divergence": divergence,
                        "terminal_deltas": candidate.terminal_deltas_from_batch_0,
                    }
                )
            comparisons.append(
                {
                    "completed_batch_count": batch,
                    "episodes_with_greedy_divergence": divergence_count,
                    "first_divergence_action_transitions": dict(
                        sorted(transitions.items())
                    ),
                    "episodes": values,
                }
            )
        return {
            "schema": self.schema,
            "training_run_sha256": self.training_run_sha256,
            "fixed_corpus_sha256": self.fixed_corpus_sha256,
            "action_schema_version": self.action_schema_version,
            "action_schema_sha256": self.action_schema_sha256,
            "milestone_links": [asdict(link) for link in self.milestone_links],
            "checkpoint_summaries": [
                _checkpoint_summary(self.episodes, batch)
                for batch in STUDY_MILESTONE_BATCHES
            ],
            "comparisons_to_batch_0": comparisons,
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return _canonical_bytes(self.as_dict()).decode("utf-8")


def _trace_policy(
    model: PPOActorCritic,
    spec: FixedSeededEpisodeSpec,
    batch_count: int,
    terminal_deltas: dict[str, float | int],
    environment: BalatroHeadlessEnvironment,
) -> PPOProgressBehaviorEpisode:
    environment.reset(seed=spec.game_seed)
    if (
        environment.frame.info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA
        or environment.frame.info.get("reward_contract") != PPO_REWARD_CONTRACT
    ):
        raise PPOContractError("PPO progress behavior environment provenance drifted")
    frames = [deepcopy(environment.frame)]
    decisions = []
    for decision_index in range(
        PPO_PROGRESS_TRAINING_CONTRACT.maximum_episode_actions
    ):
        frame = environment.frame
        if frame.status.terminal:
            break
        observation = frame.encoded_observation()
        mask = legal_action_mask(environment.legal_actions())
        output = model.infer(observation, mask)
        if not isinstance(output, PPOPolicyOutput):
            raise PPOContractError("PPO progress behavior model output is invalid")
        allowed = tuple(index for index, value in enumerate(mask.values) if value)
        if not allowed:
            raise PPOContractError("PPO progress behavior legal action set is empty")
        selected = min(
            allowed, key=lambda index: (-output.probabilities[index], index)
        )
        entropy = -math.fsum(
            probability * math.log(probability)
            for index in allowed
            if (probability := output.probabilities[index]) > 0.0
        )
        decisions.append(
            PPOProgressBehaviorDecision(
                decision_index,
                sha256(_canonical_bytes(list(observation.values))).hexdigest(),
                allowed,
                selected,
                output.probabilities[selected],
                entropy,
                output.value_estimate,
            )
        )
        _, _, terminated, truncated, info = environment.step(
            action_from_index(selected)
        )
        if truncated:
            raise PPOContractError("PPO progress behavior episode truncated")
        if (
            info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA
            or info.get("reward_contract") != PPO_REWARD_CONTRACT
        ):
            raise PPOContractError("PPO progress behavior environment drifted")
        frames.append(deepcopy(environment.frame))
        if terminated:
            break
    else:
        raise PPOContractError("PPO progress behavior exceeded the action cap")
    if not environment.frame.status.terminal:
        raise PPOContractError("PPO progress behavior episode is incomplete")
    metrics = derive_terminal_episode_metrics(
        status=environment.frame.status,
        action_count=len(decisions),
        frames=frames,
    )
    return PPOProgressBehaviorEpisode(
        batch_count,
        spec.episode_index,
        spec.game_seed,
        environment.frame.status.value,
        metrics,
        tuple(decisions),
        terminal_deltas,
    )


_WORKER_MODELS: tuple[tuple[int, PPOActorCritic], ...] = ()
_WORKER_DELTAS: dict[tuple[int, int], dict[str, float | int]] = {}
_WORKER_ENVIRONMENT: BalatroHeadlessEnvironment | None = None


def _initialize_worker(models, deltas) -> None:
    global _WORKER_MODELS, _WORKER_DELTAS, _WORKER_ENVIRONMENT
    _WORKER_MODELS = models
    _WORKER_DELTAS = deltas
    _WORKER_ENVIRONMENT = make_ppo_training_environment(0)


def _trace_worker(spec: FixedSeededEpisodeSpec) -> tuple[PPOProgressBehaviorEpisode, ...]:
    if not _WORKER_MODELS or _WORKER_ENVIRONMENT is None:
        raise PPOContractError("PPO progress behavior worker is uninitialized")
    return tuple(
        _trace_policy(
            model,
            spec,
            batch,
            _WORKER_DELTAS[(batch, spec.episode_index)],
            _WORKER_ENVIRONMENT,
        )
        for batch, model in _WORKER_MODELS
    )


def run_progress_study_behavior_attribution(
    artifact_directory: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    seed_executor=None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> PPOProgressBehaviorReport:
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("PPO progress behavior workers must be from 1 through 8")
    if seed_executor is not None and not callable(seed_executor):
        raise TypeError("PPO progress behavior executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("PPO progress behavior callback must be callable")
    destination = Path(output_path)
    if destination.exists():
        raise PPOContractError("PPO progress behavior output already exists")
    if not destination.parent.is_dir():
        raise PPOContractError("PPO progress behavior output directory is missing")
    directory = Path(artifact_directory)
    run, _ = initialize_progress_study(directory)
    models = []
    links = []
    deltas = {}
    expected_outcomes = {}
    for batch in STUDY_MILESTONE_BATCHES:
        milestone = load_progress_study_milestone(directory, run, batch)
        evaluation = load_progress_study_evaluation(directory, run, batch)
        milestone_directory = (
            directory / STUDY_MILESTONE_DIRECTORY / f"batch-{batch:03d}"
        )
        links.append(
            PPOProgressBehaviorMilestoneLink(
                batch,
                sha256(
                    (milestone_directory / STUDY_MILESTONE_MANIFEST_NAME).read_bytes()
                ).hexdigest(),
                sha256(
                    (milestone_directory / STUDY_EVALUATION_NAME).read_bytes()
                ).hexdigest(),
                milestone.milestone.policy_parameter_sha256,
            )
        )
        models.append((batch, milestone.session.learner.model))
        for episode in evaluation.episodes:
            deltas[(batch, episode.episode_index)] = episode.as_dict()["deltas"]
            expected_outcomes[(batch, episode.episode_index)] = (
                episode.initial if batch == 0 else episode.one_batch
            )
    episode_values = []

    def record(values) -> None:
        if (
            not isinstance(values, tuple)
            or tuple(episode.completed_batch_count for episode in values)
            != STUDY_MILESTONE_BATCHES
        ):
            raise PPOContractError("PPO progress behavior seed result is malformed")
        episode_values.extend(values)
        if progress_callback is not None:
            progress_callback(
                len(episode_values) // len(STUDY_MILESTONE_BATCHES),
                len(FIXED_SEEDED_EPISODES),
            )

    model_tuple = tuple(models)
    if seed_executor is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(model_tuple, deltas),
        ) as executor:
            for values in executor.map(_trace_worker, FIXED_SEEDED_EPISODES):
                record(values)
    else:
        for spec in FIXED_SEEDED_EPISODES:
            record(seed_executor(spec, model_tuple, deltas))
    by_key = {
        (episode.completed_batch_count, episode.episode_index): episode
        for episode in episode_values
    }
    episodes = tuple(
        by_key[(batch, spec.episode_index)]
        for batch in STUDY_MILESTONE_BATCHES
        for spec in FIXED_SEEDED_EPISODES
    )
    for episode in episodes:
        expected = expected_outcomes[
            (episode.completed_batch_count, episode.episode_index)
        ]
        if (
            episode.status != expected.status
            or len(episode.decisions) != expected.action_count
            or episode.metrics != expected.metrics
        ):
            raise PPOContractError("PPO progress behavior terminal evidence drifted")
    report = PPOProgressBehaviorReport(
        PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA,
        run.sha256,
        FIXED_SEEDED_CORPUS_SHA256,
        PUBLIC_ACTION_VERSION,
        ACTION_SCHEMA_SHA256,
        tuple(links),
        episodes,
    )
    _atomic_write(destination, report.to_json().encode("utf-8"))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"completed_seeds": completed, "total_seeds": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_progress_study_behavior_attribution(
        arguments.artifact_directory,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.output_path)
    print(
        _canonical_bytes(
            {
                "schema": report.schema,
                "output_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
