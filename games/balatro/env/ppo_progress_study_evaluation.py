"""Immutable fixed-corpus evaluation for one progress-study milestone."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from games.balatro.env.evaluation_diagnostics import TerminalEpisodeMetrics
from games.balatro.env.ppo_campaign import _atomic_write
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_progress_reward_evaluation import (
    PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
    PPOProgressPairedEpisode,
    PPOProgressPolicyOutcome,
    evaluate_progress_policy_corpus_pair,
    summarize_progress_policy_outcomes,
)
from games.balatro.env.ppo_progress_study import (
    STUDY_MILESTONE_BATCHES,
    STUDY_MILESTONE_DIRECTORY,
    STUDY_MILESTONE_MANIFEST_NAME,
    load_progress_study_milestone,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)


PPO_PROGRESS_STUDY_EVALUATION_SCHEMA = (
    "balatro-red-white-progress-study-paired-evaluation-v1"
)
STUDY_EVALUATION_NAME = "evaluation.json"


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOContractError("PPO progress study evaluation is not canonical") from error


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOContractError(f"PPO progress study evaluation {label} is invalid")
    return value


@dataclass(frozen=True)
class PPOProgressStudyEvaluationReport:
    schema: str
    fixed_corpus_sha256: str
    selection_contract: str
    training_run_sha256: str
    completed_batch_count: int
    initial_milestone_sha256: str
    candidate_milestone_sha256: str
    initial_policy_parameter_sha256: str
    candidate_policy_parameter_sha256: str
    episodes: tuple[PPOProgressPairedEpisode, ...]

    def __post_init__(self) -> None:
        if self.schema != PPO_PROGRESS_STUDY_EVALUATION_SCHEMA:
            raise PPOContractError("PPO progress study evaluation schema mismatch")
        if self.fixed_corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise PPOContractError("PPO progress study evaluation corpus drifted")
        if self.selection_contract != PPO_PROGRESS_GREEDY_SELECTION_CONTRACT:
            raise PPOContractError("PPO progress study evaluation selection drifted")
        if self.completed_batch_count not in STUDY_MILESTONE_BATCHES:
            raise PPOContractError("PPO progress study evaluation batch is not staged")
        for name in (
            "training_run_sha256",
            "initial_milestone_sha256",
            "candidate_milestone_sha256",
            "initial_policy_parameter_sha256",
            "candidate_policy_parameter_sha256",
        ):
            _digest(getattr(self, name), name)
        expected = tuple(
            (spec.episode_index, spec.game_seed) for spec in FIXED_SEEDED_EPISODES
        )
        actual = (
            tuple((episode.episode_index, episode.game_seed) for episode in self.episodes)
            if isinstance(self.episodes, tuple)
            else ()
        )
        if actual != expected:
            raise PPOContractError(
                "PPO progress study evaluation episodes are incomplete or out of order"
            )

    def as_dict(self) -> dict[str, Any]:
        initial = summarize_progress_policy_outcomes(self.episodes, "initial")
        candidate = summarize_progress_policy_outcomes(self.episodes, "one_batch")
        episodes = []
        for episode in self.episodes:
            value = episode.as_dict()
            episodes.append(
                {
                    "episode_index": value["episode_index"],
                    "game_seed": value["game_seed"],
                    "batch_0": value["initial"],
                    "candidate": value["one_batch"],
                    "deltas": value["deltas"],
                }
            )
        return {
            "schema": self.schema,
            "fixed_corpus_sha256": self.fixed_corpus_sha256,
            "selection_contract": self.selection_contract,
            "training_run_sha256": self.training_run_sha256,
            "completed_batch_count": self.completed_batch_count,
            "initial_milestone_sha256": self.initial_milestone_sha256,
            "candidate_milestone_sha256": self.candidate_milestone_sha256,
            "initial_policy_parameter_sha256": self.initial_policy_parameter_sha256,
            "candidate_policy_parameter_sha256": self.candidate_policy_parameter_sha256,
            "summary": {
                "batch_0": initial,
                "candidate": candidate,
                "deltas": {
                    key: candidate[key] - initial[key]
                    for key in initial
                    if key != "episode_count"
                },
            },
            "episodes": episodes,
        }

    def to_json(self) -> str:
        return _canonical_bytes(self.as_dict()).decode("utf-8")


def _manifest_path(directory: Path, batch_count: int) -> Path:
    return (
        directory
        / STUDY_MILESTONE_DIRECTORY
        / f"batch-{batch_count:03d}"
        / STUDY_MILESTONE_MANIFEST_NAME
    )


def _evaluation_path(directory: Path, batch_count: int) -> Path:
    return _manifest_path(directory, batch_count).with_name(STUDY_EVALUATION_NAME)


def run_progress_study_evaluation(
    artifact_directory: str | Path,
    training_run: PPOTrainingRun,
    batch_count: int,
    *,
    maximum_workers: int,
    pair_executor=None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> PPOProgressStudyEvaluationReport:
    directory = Path(artifact_directory)
    destination = _evaluation_path(directory, batch_count)
    if destination.exists():
        raise PPOContractError("PPO progress study evaluation already exists")
    initial = load_progress_study_milestone(directory, training_run, 0)
    candidate = load_progress_study_milestone(directory, training_run, batch_count)
    initial_manifest = _manifest_path(directory, 0).read_bytes()
    candidate_manifest = _manifest_path(directory, batch_count).read_bytes()
    episodes = evaluate_progress_policy_corpus_pair(
        initial.session.learner.model,
        candidate.session.learner.model,
        maximum_workers=maximum_workers,
        pair_executor=pair_executor,
        progress_callback=progress_callback,
    )
    report = PPOProgressStudyEvaluationReport(
        schema=PPO_PROGRESS_STUDY_EVALUATION_SCHEMA,
        fixed_corpus_sha256=FIXED_SEEDED_CORPUS_SHA256,
        selection_contract=PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
        training_run_sha256=training_run.sha256,
        completed_batch_count=batch_count,
        initial_milestone_sha256=sha256(initial_manifest).hexdigest(),
        candidate_milestone_sha256=sha256(candidate_manifest).hexdigest(),
        initial_policy_parameter_sha256=(
            initial.milestone.policy_parameter_sha256
        ),
        candidate_policy_parameter_sha256=(
            candidate.milestone.policy_parameter_sha256
        ),
        episodes=episodes,
    )
    _atomic_write(destination, report.to_json().encode("utf-8"))
    return report


def load_progress_study_evaluation(
    artifact_directory: str | Path,
    training_run: PPOTrainingRun,
    batch_count: int,
) -> PPOProgressStudyEvaluationReport:
    directory = Path(artifact_directory)
    path = _evaluation_path(directory, batch_count)
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError("PPO progress study evaluation is unreadable") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise PPOContractError("PPO progress study evaluation is noncanonical")
    try:
        episodes = tuple(
            PPOProgressPairedEpisode(
                episode["episode_index"],
                episode["game_seed"],
                PPOProgressPolicyOutcome(
                    episode["batch_0"]["status"],
                    episode["batch_0"]["action_count"],
                    TerminalEpisodeMetrics(**episode["batch_0"]["metrics"]),
                ),
                PPOProgressPolicyOutcome(
                    episode["candidate"]["status"],
                    episode["candidate"]["action_count"],
                    TerminalEpisodeMetrics(**episode["candidate"]["metrics"]),
                ),
            )
            for episode in value["episodes"]
        )
        report = PPOProgressStudyEvaluationReport(
            schema=value["schema"],
            fixed_corpus_sha256=value["fixed_corpus_sha256"],
            selection_contract=value["selection_contract"],
            training_run_sha256=value["training_run_sha256"],
            completed_batch_count=value["completed_batch_count"],
            initial_milestone_sha256=value["initial_milestone_sha256"],
            candidate_milestone_sha256=value["candidate_milestone_sha256"],
            initial_policy_parameter_sha256=value[
                "initial_policy_parameter_sha256"
            ],
            candidate_policy_parameter_sha256=value[
                "candidate_policy_parameter_sha256"
            ],
            episodes=episodes,
        )
    except (KeyError, TypeError, PPOContractError) as error:
        raise PPOContractError("PPO progress study evaluation is malformed") from error
    initial = load_progress_study_milestone(directory, training_run, 0)
    candidate = load_progress_study_milestone(directory, training_run, batch_count)
    if (
        report.to_json().encode("utf-8") != raw
        or report.training_run_sha256 != training_run.sha256
        or report.initial_milestone_sha256
        != sha256(_manifest_path(directory, 0).read_bytes()).hexdigest()
        or report.candidate_milestone_sha256
        != sha256(_manifest_path(directory, batch_count).read_bytes()).hexdigest()
        or report.initial_policy_parameter_sha256
        != initial.milestone.policy_parameter_sha256
        or report.candidate_policy_parameter_sha256
        != candidate.milestone.policy_parameter_sha256
    ):
        raise PPOContractError("PPO progress study evaluation linkage drifted")
    return report
