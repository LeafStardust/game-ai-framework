"""Crash-consistent metric journal for the capped progress-reward study."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from games.balatro.env.ppo_campaign import _atomic_write
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import compute_gae


PPO_PROGRESS_STUDY_JOURNAL_SCHEMA = "balatro-red-white-progress-study-journal-v1"
STUDY_JOURNAL_NAME = "study_journal.json"


def _lower_digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOContractError(f"PPO progress study {label} digest is invalid")
    return value


def _exact_nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PPOContractError(f"PPO progress study {label} is invalid")
    return value


@dataclass(frozen=True)
class PPOProgressStudyEpisodeRecord:
    training_run_sha256: str
    episode_index: int
    game_seed: str
    status: str
    action_count: int
    completed_batch_count_after_commit: int
    collected_transition_count_after_commit: int
    policy_parameter_sha256_after_commit: str
    rewards: tuple[float, ...]
    advantages: tuple[float, ...]

    def __post_init__(self) -> None:
        _lower_digest(self.training_run_sha256, "training run")
        _lower_digest(self.policy_parameter_sha256_after_commit, "policy parameter")
        _exact_nonnegative(self.episode_index, "episode index")
        if not isinstance(self.game_seed, str) or not self.game_seed:
            raise PPOContractError("PPO progress study game seed is invalid")
        if self.status not in {"LOSS", "ANTE_8_WIN"}:
            raise PPOContractError("PPO progress study terminal status is invalid")
        if _exact_nonnegative(self.action_count, "action count") < 1:
            raise PPOContractError("PPO progress study action count is invalid")
        batches = _exact_nonnegative(
            self.completed_batch_count_after_commit, "batch count"
        )
        if batches > 8:
            raise PPOContractError("PPO progress study batch count exceeds 8")
        collected = _exact_nonnegative(
            self.collected_transition_count_after_commit, "transition count"
        )
        if collected < self.action_count:
            raise PPOContractError("PPO progress study transition count drifted")
        if (
            not isinstance(self.rewards, tuple)
            or not isinstance(self.advantages, tuple)
            or len(self.rewards) != self.action_count
            or len(self.advantages) != self.action_count
        ):
            raise PPOContractError("PPO progress study signal lengths drifted")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (*self.rewards, *self.advantages)
        ):
            raise PPOContractError("PPO progress study signal is nonfinite")

    @classmethod
    def from_episode(
        cls, session: object, episode: PPORolloutEpisode
    ) -> "PPOProgressStudyEpisodeRecord":
        if not isinstance(episode, PPORolloutEpisode):
            raise TypeError("episode must be PPORolloutEpisode")
        training_run = getattr(session, "training_run", None)
        learner = getattr(session, "learner", None)
        if (
            not isinstance(training_run, PPOTrainingRun)
            or training_run != episode.training_run
            or training_run.contract_sha256 != PPO_PROGRESS_TRAINING_CONTRACT.sha256
            or learner is None
        ):
            raise PPOContractError("PPO progress study episode provenance drifted")
        rewards = np.asarray(episode.rewards, dtype=np.float64)
        values = np.asarray(
            [decision.value_estimate for decision in episode.decisions],
            dtype=np.float64,
        )
        terminals = np.zeros(episode.action_count, dtype=np.bool_)
        terminals[-1] = True
        advantages, _ = compute_gae(rewards, values, terminals)
        return cls(
            training_run_sha256=training_run.sha256,
            episode_index=episode.episode_index,
            game_seed=episode.game_seed,
            status=episode.status.value,
            action_count=episode.action_count,
            completed_batch_count_after_commit=learner.completed_batch_count,
            collected_transition_count_after_commit=(
                learner.total_consumed_environment_transitions
            ),
            policy_parameter_sha256_after_commit=learner.model.parameter_sha256,
            rewards=tuple(float(value) for value in rewards),
            advantages=tuple(float(value) for value in advantages),
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rewards"] = list(self.rewards)
        value["advantages"] = list(self.advantages)
        return value


@dataclass(frozen=True)
class PPOProgressStudyJournal:
    schema: str
    training_run_sha256: str
    records: tuple[PPOProgressStudyEpisodeRecord, ...] = ()

    def __post_init__(self) -> None:
        if self.schema != PPO_PROGRESS_STUDY_JOURNAL_SCHEMA:
            raise PPOContractError("PPO progress study journal schema mismatch")
        _lower_digest(self.training_run_sha256, "journal training run")
        if not isinstance(self.records, tuple) or any(
            not isinstance(record, PPOProgressStudyEpisodeRecord)
            or record.training_run_sha256 != self.training_run_sha256
            for record in self.records
        ):
            raise PPOContractError("PPO progress study journal records are invalid")
        if tuple(record.episode_index for record in self.records) != tuple(
            range(len(self.records))
        ):
            raise PPOContractError("PPO progress study journal order drifted")
        previous_transitions = 0
        previous_batches = 0
        for record in self.records:
            if (
                record.collected_transition_count_after_commit
                != previous_transitions + record.action_count
                or record.completed_batch_count_after_commit < previous_batches
                or record.completed_batch_count_after_commit > previous_batches + 1
            ):
                raise PPOContractError("PPO progress study journal counters drifted")
            previous_transitions = record.collected_transition_count_after_commit
            previous_batches = record.completed_batch_count_after_commit

    @classmethod
    def fresh(cls, training_run: PPOTrainingRun) -> "PPOProgressStudyJournal":
        if (
            not isinstance(training_run, PPOTrainingRun)
            or training_run.contract_sha256 != PPO_PROGRESS_TRAINING_CONTRACT.sha256
        ):
            raise PPOContractError("PPO progress study requires the v2 training run")
        return cls(PPO_PROGRESS_STUDY_JOURNAL_SCHEMA, training_run.sha256)

    def append(
        self, record: PPOProgressStudyEpisodeRecord
    ) -> "PPOProgressStudyJournal":
        return PPOProgressStudyJournal(
            self.schema, self.training_run_sha256, self.records + (record,)
        )

    def reconciled(
        self, next_episode_indices: tuple[int, ...]
    ) -> "PPOProgressStudyJournal":
        count = PPO_PROGRESS_TRAINING_CONTRACT.parallel_environments
        if (
            not isinstance(next_episode_indices, tuple)
            or len(next_episode_indices) != count
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < stream
                or value % count != stream
                for stream, value in enumerate(next_episode_indices)
            )
        ):
            raise PPOContractError("PPO progress study checkpoint indices are invalid")
        committed_indices = tuple(
            sorted(
                index
                for stream, stop in enumerate(next_episode_indices)
                for index in range(stream, stop, count)
            )
        )
        if committed_indices != tuple(range(len(committed_indices))):
            raise PPOContractError("PPO progress study checkpoint order drifted")
        committed_count = len(committed_indices)
        if len(self.records) < committed_count:
            raise PPOContractError("PPO progress study journal is behind checkpoint")
        if len(self.records) > committed_count + 1:
            raise PPOContractError("PPO progress study journal is too far ahead")
        if tuple(record.episode_index for record in self.records[:committed_count]) != (
            committed_indices
        ):
            raise PPOContractError("PPO progress study journal/checkpoint drifted")
        return PPOProgressStudyJournal(
            self.schema,
            self.training_run_sha256,
            self.records[:committed_count],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "training_run_sha256": self.training_run_sha256,
            "records": [record.as_dict() for record in self.records],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def write_progress_study_journal(
    path: str | Path, journal: PPOProgressStudyJournal
) -> None:
    if not isinstance(journal, PPOProgressStudyJournal):
        raise TypeError("journal must be PPOProgressStudyJournal")
    _atomic_write(Path(path), journal.to_json().encode("utf-8"))


def load_progress_study_journal(
    path: str | Path, training_run: PPOTrainingRun
) -> PPOProgressStudyJournal:
    journal_path = Path(path)
    if not journal_path.exists():
        return PPOProgressStudyJournal.fresh(training_run)
    try:
        raw = journal_path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError("PPO progress study journal is unreadable") from error
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "training_run_sha256", "records"}
        or json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        != raw
        or value["training_run_sha256"] != training_run.sha256
        or not isinstance(value["records"], list)
    ):
        raise PPOContractError("PPO progress study journal provenance drifted")
    try:
        records = tuple(
            PPOProgressStudyEpisodeRecord(
                **{
                    **record,
                    "rewards": tuple(record["rewards"]),
                    "advantages": tuple(record["advantages"]),
                }
            )
            for record in value["records"]
        )
    except (KeyError, TypeError, PPOContractError) as error:
        raise PPOContractError("PPO progress study journal records are malformed") from error
    return PPOProgressStudyJournal(
        value["schema"], value["training_run_sha256"], records
    )
