"""Versioned resumable owner for deterministic PPO learner state."""

from __future__ import annotations

from base64 import b64decode, b64encode
from copy import deepcopy
from hashlib import sha256
import math
from typing import Any

import numpy as np

from games.balatro.env.ppo_batch import (
    PPO_BATCH_ASSEMBLER_VERSION,
    PPOBatchAssembler,
)
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import (
    PPO_MODEL_VERSION,
    PPO_OPTIMIZER_VERSION,
    PPOActorCritic,
    PPOLoss,
    PPOOptimizer,
)


PPO_LEARNER_CHECKPOINT_VERSION = "balatro-red-white-ppo-learner-checkpoint-v1"
_ARRAY_FIELDS = {"dtype", "shape", "data_base64", "sha256"}


def _exact_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PPOContractError(f"{name} must be a nonnegative exact integer")
    return value


def _encode_array(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(value, dtype="<f8")
    if not np.all(np.isfinite(array)):
        raise PPOContractError("PPO learner checkpoint arrays must be finite")
    raw = array.tobytes()
    return {
        "dtype": "<f8",
        "shape": list(array.shape),
        "data_base64": b64encode(raw).decode("ascii"),
        "sha256": sha256(raw).hexdigest(),
    }


def _decode_array(value: object, expected_shape: tuple[int, ...], name: str) -> np.ndarray:
    if not isinstance(value, dict) or set(value) != _ARRAY_FIELDS:
        raise PPOContractError(f"{name} array fields are incomplete")
    if value["dtype"] != "<f8" or value["shape"] != list(expected_shape):
        raise PPOContractError(f"{name} array shape or dtype drifted")
    encoded = value["data_base64"]
    digest = value["sha256"]
    if not isinstance(encoded, str) or not isinstance(digest, str):
        raise PPOContractError(f"{name} array encoding is malformed")
    try:
        raw = b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise PPOContractError(f"{name} array encoding is malformed") from error
    if b64encode(raw).decode("ascii") != encoded or sha256(raw).hexdigest() != digest:
        raise PPOContractError(f"{name} array digest is invalid")
    expected_bytes = math.prod(expected_shape) * np.dtype("<f8").itemsize
    if len(raw) != expected_bytes:
        raise PPOContractError(f"{name} array byte length drifted")
    array = np.frombuffer(raw, dtype="<f8").reshape(expected_shape).copy()
    if not np.all(np.isfinite(array)):
        raise PPOContractError(f"{name} array must be finite")
    return array


class PPOLearner:
    """Own model, optimizer, assembly, counters, and exact checkpoint restore."""

    def __init__(self, training_run: PPOTrainingRun):
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        self.training_run = training_run
        self.model = PPOActorCritic(training_run)
        self.optimizer = PPOOptimizer(self.model, training_run)
        self.assembler = PPOBatchAssembler(training_run)
        self.completed_batch_count = 0
        self.total_consumed_environment_transitions = 0

    def add_episode(self, episode: PPORolloutEpisode) -> None:
        self.assembler.add_episode(episode)
        self.total_consumed_environment_transitions += episode.action_count

    def update_ready_batch(self) -> tuple[PPOLoss, ...]:
        batch = self.assembler.assemble()
        losses = self.optimizer.update(batch)
        self.completed_batch_count += 1
        return losses

    def _validate_counters(self) -> None:
        updates_per_batch = (
            PPO_TRAINING_CONTRACT.update_epochs
            * PPO_TRAINING_CONTRACT.rollout_batch_size
            // PPO_TRAINING_CONTRACT.minibatch_size
        )
        if self.optimizer._steps != self.completed_batch_count * updates_per_batch:
            raise PPOContractError("PPO learner optimizer-step counter drifted")
        accounted = (
            self.completed_batch_count * PPO_TRAINING_CONTRACT.rollout_batch_size
            + sum(self.assembler.carryover_counts)
        )
        if self.total_consumed_environment_transitions != accounted:
            raise PPOContractError("PPO learner environment-transition counter drifted")

    def serialize(self) -> dict[str, Any]:
        self._validate_counters()
        parameter_names = tuple(self.model.parameters)
        return {
            "version": PPO_LEARNER_CHECKPOINT_VERSION,
            "training_run_sha256": self.training_run.sha256,
            "model_version": PPO_MODEL_VERSION,
            "optimizer_version": PPO_OPTIMIZER_VERSION,
            "assembler_version": PPO_BATCH_ASSEMBLER_VERSION,
            "parameters": {
                name: _encode_array(self.model.parameters[name])
                for name in parameter_names
            },
            "adam_first_moments": {
                name: _encode_array(self.optimizer._first[name])
                for name in parameter_names
            },
            "adam_second_moments": {
                name: _encode_array(self.optimizer._second[name])
                for name in parameter_names
            },
            "adam_step": self.optimizer._steps,
            "minibatch_rng_state": deepcopy(self.optimizer._rng.bit_generator.state),
            "assembler": self.assembler.serialize(),
            "completed_batch_count": self.completed_batch_count,
            "total_consumed_environment_transitions": (
                self.total_consumed_environment_transitions
            ),
        }

    @classmethod
    def restore(cls, training_run: PPOTrainingRun, payload: object) -> "PPOLearner":
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        fields = {
            "version",
            "training_run_sha256",
            "model_version",
            "optimizer_version",
            "assembler_version",
            "parameters",
            "adam_first_moments",
            "adam_second_moments",
            "adam_step",
            "minibatch_rng_state",
            "assembler",
            "completed_batch_count",
            "total_consumed_environment_transitions",
        }
        if not isinstance(payload, dict) or set(payload) != fields:
            raise PPOContractError("PPO learner checkpoint fields are incomplete")
        versions = (
            (payload["version"], PPO_LEARNER_CHECKPOINT_VERSION, "checkpoint"),
            (payload["model_version"], PPO_MODEL_VERSION, "model"),
            (payload["optimizer_version"], PPO_OPTIMIZER_VERSION, "optimizer"),
            (payload["assembler_version"], PPO_BATCH_ASSEMBLER_VERSION, "assembler"),
        )
        for actual, expected, label in versions:
            if actual != expected:
                raise PPOContractError(f"PPO learner {label} version mismatch")
        if payload["training_run_sha256"] != training_run.sha256:
            raise PPOContractError("PPO learner training-run provenance mismatch")

        learner = cls(training_run)
        names = set(learner.model.parameters)
        array_groups = (
            (payload["parameters"], learner.model.parameters, "parameter"),
            (payload["adam_first_moments"], learner.optimizer._first, "first moment"),
            (payload["adam_second_moments"], learner.optimizer._second, "second moment"),
        )
        for encoded_group, target_group, label in array_groups:
            if not isinstance(encoded_group, dict) or set(encoded_group) != names:
                raise PPOContractError(f"PPO learner {label} names drifted")
            for name in target_group:
                target_group[name] = _decode_array(
                    encoded_group[name],
                    target_group[name].shape,
                    f"PPO learner {label} {name}",
                )

        learner.optimizer._steps = _exact_nonnegative_int(
            payload["adam_step"], "Adam step"
        )
        rng_state = payload["minibatch_rng_state"]
        try:
            learner.optimizer._rng.bit_generator.state = deepcopy(rng_state)
        except (TypeError, ValueError, KeyError) as error:
            raise PPOContractError("PPO learner minibatch RNG state is invalid") from error
        learner.assembler = PPOBatchAssembler.restore(training_run, payload["assembler"])
        learner.completed_batch_count = _exact_nonnegative_int(
            payload["completed_batch_count"], "completed batch count"
        )
        learner.total_consumed_environment_transitions = _exact_nonnegative_int(
            payload["total_consumed_environment_transitions"],
            "total consumed environment transitions",
        )
        learner._validate_counters()
        return learner
