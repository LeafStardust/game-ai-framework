"""Versioned complete-episode assembly for frozen PPO training batches."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOBatch, compute_gae


PPO_BATCH_ASSEMBLER_VERSION = "balatro-red-white-ppo-batch-assembler-v1"


@dataclass(frozen=True)
class _Transition:
    observation: tuple[float, ...]
    action_mask: tuple[bool, ...]
    action_index: int
    episode_index: int
    decision_index: int
    old_log_probability: float
    old_value: float
    advantage: float
    return_value: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation": list(self.observation),
            "action_mask": list(self.action_mask),
            "action_index": self.action_index,
            "episode_index": self.episode_index,
            "decision_index": self.decision_index,
            "old_log_probability": self.old_log_probability,
            "old_value": self.old_value,
            "advantage": self.advantage,
            "return_value": self.return_value,
        }

    @classmethod
    def from_dict(cls, value: object) -> "_Transition":
        fields = {
            "observation",
            "action_mask",
            "action_index",
            "episode_index",
            "decision_index",
            "old_log_probability",
            "old_value",
            "advantage",
            "return_value",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise PPOContractError("PPO carryover transition fields are incomplete")
        observation = np.asarray(value["observation"], dtype=np.float64)
        mask = np.asarray(value["action_mask"])
        action = value["action_index"]
        episode_index = value["episode_index"]
        decision_index = value["decision_index"]
        numbers = tuple(value[name] for name in (
            "old_log_probability", "old_value", "advantage", "return_value"
        ))
        if (
            observation.shape != (PPO_TRAINING_CONTRACT.observation_size,)
            or not np.all(np.isfinite(observation))
        ):
            raise PPOContractError("PPO carryover observation is malformed")
        if (
            mask.shape != (PPO_TRAINING_CONTRACT.action_size,)
            or mask.dtype != np.bool_
            or not np.any(mask)
        ):
            raise PPOContractError("PPO carryover action mask is malformed")
        if (
            isinstance(action, bool)
            or not isinstance(action, int)
            or action < 0
            or action >= len(mask)
            or not mask[action]
        ):
            raise PPOContractError("PPO carryover action is illegal")
        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in (episode_index, decision_index)
        ):
            raise PPOContractError("PPO carryover provenance indices are invalid")
        if any(
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            for number in numbers
        ):
            raise PPOContractError("PPO carryover values must be finite")
        return cls(
            tuple(float(item) for item in observation),
            tuple(bool(item) for item in mask),
            action,
            episode_index,
            decision_index,
            *(float(number) for number in numbers),
        )


class PPOBatchAssembler:
    """Queue complete episodes into eight exact 256-transition stream slices."""

    def __init__(self, training_run: PPOTrainingRun):
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        self.training_run = training_run
        count = PPO_TRAINING_CONTRACT.parallel_environments
        self._streams: list[list[_Transition]] = [[] for _ in range(count)]
        self._next_episode_indices = list(range(count))

    @property
    def carryover_counts(self) -> tuple[int, ...]:
        return tuple(len(stream) for stream in self._streams)

    @property
    def next_episode_indices(self) -> tuple[int, ...]:
        return tuple(self._next_episode_indices)

    @property
    def ready(self) -> bool:
        required = PPO_TRAINING_CONTRACT.rollout_steps_per_environment
        return all(len(stream) >= required for stream in self._streams)

    def add_episode(self, episode: PPORolloutEpisode) -> None:
        if not isinstance(episode, PPORolloutEpisode):
            raise TypeError("episode must be PPORolloutEpisode")
        if episode.training_run != self.training_run:
            raise PPOContractError("PPO batch episode training-run provenance mismatch")
        stream_index = episode.episode_index % PPO_TRAINING_CONTRACT.parallel_environments
        if episode.episode_index != self._next_episode_indices[stream_index]:
            raise PPOContractError("PPO batch episode index is out of stream order")

        rewards = np.asarray(episode.rewards, dtype=np.float64)
        values = np.asarray(
            [decision.value_estimate for decision in episode.decisions],
            dtype=np.float64,
        )
        terminals = np.zeros(len(episode.decisions), dtype=np.bool_)
        terminals[-1] = True
        advantages, returns = compute_gae(rewards, values, terminals)
        transitions: list[_Transition] = []
        for index, decision in enumerate(episode.decisions):
            probability = decision.probabilities[decision.action_index]
            if probability <= 0.0 or not math.isfinite(probability):
                raise PPOContractError("PPO batch selected old probability is invalid")
            transitions.append(
                _Transition(
                    observation=decision.observation.values,
                    action_mask=decision.action_mask.values,
                    action_index=decision.action_index,
                    episode_index=episode.episode_index,
                    decision_index=index,
                    old_log_probability=math.log(probability),
                    old_value=decision.value_estimate,
                    advantage=float(advantages[index]),
                    return_value=float(returns[index]),
                )
            )
        self._streams[stream_index].extend(transitions)
        self._next_episode_indices[stream_index] += (
            PPO_TRAINING_CONTRACT.parallel_environments
        )

    def assemble(self) -> PPOBatch:
        if not self.ready:
            raise PPOContractError("PPO batch assembler has insufficient stream transitions")
        per_stream = PPO_TRAINING_CONTRACT.rollout_steps_per_environment
        selected: list[_Transition] = []
        for stream in self._streams:
            selected.extend(stream[:per_stream])
            del stream[:per_stream]
        batch = PPOBatch(
            observations=np.asarray(
                [transition.observation for transition in selected], dtype=np.float64
            ),
            action_masks=np.asarray(
                [transition.action_mask for transition in selected], dtype=np.bool_
            ),
            action_indices=np.asarray(
                [transition.action_index for transition in selected], dtype=np.int64
            ),
            episode_indices=np.asarray(
                [transition.episode_index for transition in selected], dtype=np.int64
            ),
            decision_indices=np.asarray(
                [transition.decision_index for transition in selected], dtype=np.int64
            ),
            old_log_probabilities=np.asarray(
                [transition.old_log_probability for transition in selected],
                dtype=np.float64,
            ),
            old_values=np.asarray(
                [transition.old_value for transition in selected], dtype=np.float64
            ),
            advantages=np.asarray(
                [transition.advantage for transition in selected], dtype=np.float64
            ),
            returns=np.asarray(
                [transition.return_value for transition in selected], dtype=np.float64
            ),
        )
        return batch.validated(expected_size=PPO_TRAINING_CONTRACT.rollout_batch_size)

    def serialize(self) -> dict[str, Any]:
        return {
            "version": PPO_BATCH_ASSEMBLER_VERSION,
            "training_run_sha256": self.training_run.sha256,
            "next_episode_indices": list(self._next_episode_indices),
            "streams": [
                [transition.as_dict() for transition in stream]
                for stream in self._streams
            ],
        }

    @classmethod
    def restore(
        cls, training_run: PPOTrainingRun, payload: object
    ) -> "PPOBatchAssembler":
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        fields = {"version", "training_run_sha256", "next_episode_indices", "streams"}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise PPOContractError("PPO batch assembler snapshot fields are incomplete")
        if payload["version"] != PPO_BATCH_ASSEMBLER_VERSION:
            raise PPOContractError("PPO batch assembler version mismatch")
        if payload["training_run_sha256"] != training_run.sha256:
            raise PPOContractError("PPO batch assembler training-run provenance mismatch")
        count = PPO_TRAINING_CONTRACT.parallel_environments
        indices = payload["next_episode_indices"]
        streams = payload["streams"]
        if (
            not isinstance(indices, list)
            or len(indices) != count
            or not isinstance(streams, list)
            or len(streams) != count
        ):
            raise PPOContractError("PPO batch assembler stream count mismatch")
        assembler = cls(training_run)
        for stream_index, episode_index in enumerate(indices):
            if (
                isinstance(episode_index, bool)
                or not isinstance(episode_index, int)
                or episode_index < stream_index
                or episode_index % count != stream_index
            ):
                raise PPOContractError("PPO batch assembler next episode index is invalid")
        if any(not isinstance(stream, list) for stream in streams):
            raise PPOContractError("PPO batch assembler carryover streams are malformed")
        assembler._next_episode_indices = list(indices)
        assembler._streams = [
            [_Transition.from_dict(value) for value in stream]
            for stream in streams
        ]
        for stream_index, stream in enumerate(assembler._streams):
            previous: tuple[int, int] | None = None
            for transition in stream:
                current = (transition.episode_index, transition.decision_index)
                if (
                    transition.episode_index % count != stream_index
                    or transition.episode_index >= indices[stream_index]
                ):
                    raise PPOContractError("PPO carryover stream provenance is invalid")
                if previous is not None:
                    same_episode = (
                        current[0] == previous[0] and current[1] == previous[1] + 1
                    )
                    next_episode = (
                        current[0] == previous[0] + count and current[1] == 0
                    )
                    if not same_episode and not next_episode:
                        raise PPOContractError("PPO carryover transition order is invalid")
                previous = current
        return assembler
