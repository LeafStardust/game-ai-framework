"""Deterministic bounded orchestration for the frozen PPO training schedule."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode


PPO_TRAINING_SESSION_VERSION = "balatro-red-white-ppo-training-session-v1"


class _AssemblerOwner(Protocol):
    @property
    def next_episode_indices(self) -> tuple[int, ...]: ...

    @property
    def ready(self) -> bool: ...


class _ModelOwner(Protocol):
    def infer(self, observation, action_mask): ...


class _LearnerOwner(Protocol):
    training_run: PPOTrainingRun
    assembler: _AssemblerOwner
    model: _ModelOwner
    completed_batch_count: int
    total_consumed_environment_transitions: int

    def add_episode(self, episode: PPORolloutEpisode) -> None: ...

    def update_ready_batch(self) -> tuple: ...

    def serialize(self) -> dict[str, Any]: ...


EnvironmentFactory = Callable[[int], BalatroHeadlessEnvironment]
EpisodeCollector = Callable[..., PPORolloutEpisode]


def _exact_positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PPOContractError(f"{name} must be a positive exact integer")
    return value


@dataclass(frozen=True)
class PPOTrainingAdvance:
    episodes_collected: int
    batches_completed: int
    last_episode_index: int | None
    completed_batch_count: int
    optimizer_consumed_transitions: int
    collected_environment_transitions: int
    complete: bool


class PPOTrainingSession:
    """Advance complete episodes without hiding an unbounded training loop."""

    def __init__(
        self,
        training_run: PPOTrainingRun,
        environment_factory: EnvironmentFactory,
        *,
        learner: _LearnerOwner | None = None,
        episode_collector: EpisodeCollector = collect_complete_ppo_episode,
    ):
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        if not callable(environment_factory):
            raise TypeError("environment_factory must be callable")
        if not callable(episode_collector):
            raise TypeError("episode_collector must be callable")
        self.training_run = training_run
        self.learner: _LearnerOwner = (
            PPOLearner(training_run) if learner is None else learner
        )
        self._validate_learner()
        count = PPO_TRAINING_CONTRACT.parallel_environments
        self._environments = tuple(environment_factory(index) for index in range(count))
        if any(
            not isinstance(environment, BalatroHeadlessEnvironment)
            for environment in self._environments
        ):
            raise TypeError("environment_factory must return BalatroHeadlessEnvironment")
        self._episode_collector = episode_collector

    @property
    def target_batch_count(self) -> int:
        return (
            PPO_TRAINING_CONTRACT.total_environment_steps
            // PPO_TRAINING_CONTRACT.rollout_batch_size
        )

    @property
    def complete(self) -> bool:
        return self.learner.completed_batch_count == self.target_batch_count

    @property
    def optimizer_consumed_transitions(self) -> int:
        return (
            self.learner.completed_batch_count
            * PPO_TRAINING_CONTRACT.rollout_batch_size
        )

    def _validate_learner(self) -> None:
        learner = self.learner
        if getattr(learner, "training_run", None) != self.training_run:
            raise PPOContractError("PPO session learner training-run provenance mismatch")
        required = (
            getattr(learner, "assembler", None),
            getattr(learner, "model", None),
            getattr(learner, "completed_batch_count", None),
            getattr(learner, "total_consumed_environment_transitions", None),
        )
        if any(value is None for value in required) or any(
            not callable(getattr(learner, name, None))
            for name in ("add_episode", "update_ready_batch", "serialize")
        ):
            raise TypeError("learner does not satisfy the PPO learner owner contract")
        completed = learner.completed_batch_count
        collected = learner.total_consumed_environment_transitions
        if (
            isinstance(completed, bool)
            or not isinstance(completed, int)
            or completed < 0
            or completed > self.target_batch_count
        ):
            raise PPOContractError("PPO session completed batch count is invalid")
        if (
            isinstance(collected, bool)
            or not isinstance(collected, int)
            or collected < self.optimizer_consumed_transitions
        ):
            raise PPOContractError(
                "PPO session collected environment-transition count is invalid"
            )
        indices = learner.assembler.next_episode_indices
        count = PPO_TRAINING_CONTRACT.parallel_environments
        if (
            not isinstance(indices, tuple)
            or len(indices) != count
            or any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < stream
                or index % count != stream
                for stream, index in enumerate(indices)
            )
        ):
            raise PPOContractError("PPO session next episode indices are invalid")

    def advance(self, *, maximum_episodes: int) -> PPOTrainingAdvance:
        limit = _exact_positive_int(maximum_episodes, "maximum episodes")
        self._validate_learner()
        episodes_collected = 0
        batches_before = self.learner.completed_batch_count
        last_episode_index: int | None = None

        while episodes_collected < limit and not self.complete:
            next_indices = self.learner.assembler.next_episode_indices
            episode_index = min(next_indices)
            stream_index = episode_index % PPO_TRAINING_CONTRACT.parallel_environments
            if next_indices[stream_index] != episode_index:
                raise PPOContractError("PPO session episode scheduling drifted")
            episode = self._episode_collector(
                self._environments[stream_index],
                self.training_run,
                episode_index=episode_index,
                policy=self.learner.model.infer,
            )
            if not isinstance(episode, PPORolloutEpisode):
                raise PPOContractError("PPO session collector returned an incomplete episode")
            if episode.episode_index != episode_index:
                raise PPOContractError("PPO session collector episode index drifted")
            self.learner.add_episode(episode)
            episodes_collected += 1
            last_episode_index = episode_index

            while self.learner.assembler.ready and not self.complete:
                before = self.learner.completed_batch_count
                self.learner.update_ready_batch()
                if self.learner.completed_batch_count != before + 1:
                    raise PPOContractError("PPO session learner batch counter drifted")

        self._validate_learner()
        return PPOTrainingAdvance(
            episodes_collected=episodes_collected,
            batches_completed=self.learner.completed_batch_count - batches_before,
            last_episode_index=last_episode_index,
            completed_batch_count=self.learner.completed_batch_count,
            optimizer_consumed_transitions=self.optimizer_consumed_transitions,
            collected_environment_transitions=(
                self.learner.total_consumed_environment_transitions
            ),
            complete=self.complete,
        )

    def serialize(self) -> dict[str, Any]:
        self._validate_learner()
        return {
            "version": PPO_TRAINING_SESSION_VERSION,
            "training_run_sha256": self.training_run.sha256,
            "learner": self.learner.serialize(),
        }

    @classmethod
    def restore(
        cls,
        training_run: PPOTrainingRun,
        environment_factory: EnvironmentFactory,
        payload: object,
        *,
        episode_collector: EpisodeCollector = collect_complete_ppo_episode,
    ) -> "PPOTrainingSession":
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        fields = {"version", "training_run_sha256", "learner"}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise PPOContractError("PPO training-session checkpoint fields are incomplete")
        if payload["version"] != PPO_TRAINING_SESSION_VERSION:
            raise PPOContractError("PPO training-session version mismatch")
        if payload["training_run_sha256"] != training_run.sha256:
            raise PPOContractError("PPO training-session run provenance mismatch")
        learner = PPOLearner.restore(training_run, payload["learner"])
        return cls(
            training_run,
            environment_factory,
            learner=learner,
            episode_collector=episode_collector,
        )
