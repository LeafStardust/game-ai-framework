"""Deterministic NumPy actor-critic and clipped-PPO optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Iterator

import numpy as np

from games.balatro.env.action_encoding import ActionMask
from games.balatro.env.observation_encoding import EncodedPublicObservation
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOPolicyOutput,
    PPOTrainingRun,
)


_PARAMETER_ORDER = ("w1", "b1", "w2", "b2", "policy_w", "policy_b", "value_w", "value_b")
PPO_MODEL_VERSION = "balatro-red-white-ppo-actor-critic-v1"
PPO_OPTIMIZER_VERSION = "balatro-red-white-ppo-adam-v1"
ADAM_BETA1 = 0.9
ADAM_BETA2 = 0.999
ADAM_EPSILON = 1e-8


def _seed64(seed_hex: str, purpose: str) -> int:
    digest = sha256(f"{seed_hex}\0{purpose}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big")


def _finite_array(value: object, name: str, *, ndim: int | None = None) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if ndim is not None and result.ndim != ndim:
        raise PPOContractError(f"{name} must have {ndim} dimensions")
    if not np.all(np.isfinite(result)):
        raise PPOContractError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class PPOBatch:
    observations: np.ndarray
    action_masks: np.ndarray
    action_indices: np.ndarray
    old_log_probabilities: np.ndarray
    old_values: np.ndarray
    advantages: np.ndarray
    returns: np.ndarray

    def validated(self, *, expected_size: int | None = None) -> "PPOBatch":
        observations = _finite_array(self.observations, "observations", ndim=2)
        masks = np.asarray(self.action_masks)
        actions = np.asarray(self.action_indices)
        old_log_probabilities = _finite_array(
            self.old_log_probabilities, "old log probabilities", ndim=1
        )
        old_values = _finite_array(self.old_values, "old values", ndim=1)
        advantages = _finite_array(self.advantages, "advantages", ndim=1)
        returns = _finite_array(self.returns, "returns", ndim=1)
        size = observations.shape[0]
        if observations.shape[1] != PPO_TRAINING_CONTRACT.observation_size:
            raise PPOContractError("PPO batch observation shape mismatch")
        if masks.shape != (size, PPO_TRAINING_CONTRACT.action_size):
            raise PPOContractError("PPO batch action-mask shape mismatch")
        if masks.dtype != np.bool_:
            raise PPOContractError("PPO batch action masks must be boolean")
        if not np.all(np.any(masks, axis=1)):
            raise PPOContractError("PPO batch contains an empty nonterminal action mask")
        if actions.shape != (size,) or not np.issubdtype(actions.dtype, np.integer):
            raise PPOContractError("PPO batch action indices must be an integer vector")
        if np.any(actions < 0) or np.any(actions >= PPO_TRAINING_CONTRACT.action_size):
            raise PPOContractError("PPO batch action index is outside the action schema")
        if not np.all(masks[np.arange(size), actions]):
            raise PPOContractError("PPO batch contains an illegal selected action")
        vectors = (old_log_probabilities, old_values, advantages, returns)
        if any(vector.shape != (size,) for vector in vectors):
            raise PPOContractError("PPO batch vector lengths disagree")
        if expected_size is not None and size != expected_size:
            raise PPOContractError("PPO batch does not match the frozen rollout size")
        return PPOBatch(
            observations,
            masks,
            actions.astype(np.int64, copy=False),
            old_log_probabilities,
            old_values,
            advantages,
            returns,
        )

    def take(self, indices: np.ndarray) -> "PPOBatch":
        return PPOBatch(
            self.observations[indices],
            self.action_masks[indices],
            self.action_indices[indices],
            self.old_log_probabilities[indices],
            self.old_values[indices],
            self.advantages[indices],
            self.returns[indices],
        )


@dataclass(frozen=True)
class PPOLoss:
    total: float
    policy: float
    value: float
    entropy: float
    unclipped_gradient_norm: float | None = None
    applied_gradient_norm: float | None = None


class PPOActorCritic:
    """Frozen `(512, 256)` tanh MLP with separate policy and value heads."""

    def __init__(self, training_run: PPOTrainingRun):
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        contract = PPO_TRAINING_CONTRACT
        if contract.activation != "tanh" or contract.policy_hidden_sizes != (512, 256):
            raise PPOContractError("PPO model architecture disagrees with its contract")
        self.training_run_sha256 = training_run.sha256
        rng = np.random.default_rng(_seed64(training_run.learner_seed_hex, "parameters"))
        sizes = (contract.observation_size, *contract.policy_hidden_sizes)
        self.parameters: dict[str, np.ndarray] = {
            "w1": self._xavier(rng, sizes[0], sizes[1]),
            "b1": np.zeros(sizes[1], dtype=np.float64),
            "w2": self._xavier(rng, sizes[1], sizes[2]),
            "b2": np.zeros(sizes[2], dtype=np.float64),
            "policy_w": self._xavier(rng, sizes[2], contract.action_size),
            "policy_b": np.zeros(contract.action_size, dtype=np.float64),
            "value_w": self._xavier(rng, sizes[2], 1),
            "value_b": np.zeros(1, dtype=np.float64),
        }

    @staticmethod
    def _xavier(rng: np.random.Generator, fan_in: int, fan_out: int) -> np.ndarray:
        limit = math.sqrt(6.0 / (fan_in + fan_out))
        return rng.uniform(-limit, limit, size=(fan_in, fan_out)).astype(np.float64)

    @property
    def parameter_sha256(self) -> str:
        digest = sha256()
        for name in _PARAMETER_ORDER:
            value = self.parameters[name]
            digest.update(name.encode("ascii"))
            digest.update(str(value.shape).encode("ascii"))
            digest.update(value.astype("<f8", copy=False).tobytes())
        return digest.hexdigest()

    def _forward_arrays(
        self, observations: np.ndarray, masks: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, tuple[np.ndarray, ...]]:
        p = self.parameters
        hidden1 = np.tanh(observations @ p["w1"] + p["b1"])
        hidden2 = np.tanh(hidden1 @ p["w2"] + p["b2"])
        logits = hidden2 @ p["policy_w"] + p["policy_b"]
        masked_logits = np.where(masks, logits, -np.inf)
        maximum = np.max(masked_logits, axis=1, keepdims=True)
        exponentials = np.where(masks, np.exp(masked_logits - maximum), 0.0)
        probabilities = exponentials / np.sum(exponentials, axis=1, keepdims=True)
        values = (hidden2 @ p["value_w"] + p["value_b"]).reshape(-1)
        return probabilities, values, (observations, hidden1, hidden2, masks)

    def evaluate_batch(
        self, observations: object, action_masks: object
    ) -> tuple[np.ndarray, np.ndarray, tuple[np.ndarray, ...]]:
        values = _finite_array(observations, "observations", ndim=2)
        masks = np.asarray(action_masks)
        expected = (values.shape[0], PPO_TRAINING_CONTRACT.action_size)
        if values.shape[1] != PPO_TRAINING_CONTRACT.observation_size:
            raise PPOContractError("PPO model observation shape mismatch")
        if masks.shape != expected or masks.dtype != np.bool_:
            raise PPOContractError("PPO model action-mask shape/type mismatch")
        if not np.all(np.any(masks, axis=1)):
            raise PPOContractError("PPO model cannot infer with an empty action mask")
        return self._forward_arrays(values, masks)

    def infer(
        self, observation: EncodedPublicObservation, action_mask: ActionMask
    ) -> PPOPolicyOutput:
        if not isinstance(observation, EncodedPublicObservation):
            raise TypeError("observation must be EncodedPublicObservation")
        if observation.schema_version != PPO_TRAINING_CONTRACT.observation_version:
            raise PPOContractError("PPO model observation schema mismatch")
        if not isinstance(action_mask, ActionMask):
            raise TypeError("action_mask must be ActionMask")
        if action_mask.schema_version != PPO_TRAINING_CONTRACT.action_version:
            raise PPOContractError("PPO model action schema mismatch")
        probabilities, values, _ = self.evaluate_batch(
            np.asarray([observation.values], dtype=np.float64),
            np.asarray([action_mask.values], dtype=np.bool_),
        )
        return PPOPolicyOutput(
            schema_version=PPO_POLICY_OUTPUT_SCHEMA,
            observation_version=PPO_TRAINING_CONTRACT.observation_version,
            action_version=PPO_TRAINING_CONTRACT.action_version,
            probabilities=tuple(float(value) for value in probabilities[0]),
            value_estimate=float(values[0]),
        )


def compute_gae(
    rewards: object,
    values: object,
    terminals: object,
    *,
    next_value: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute frozen-contract generalized advantages and value returns."""
    rewards_array = _finite_array(rewards, "rewards", ndim=1)
    values_array = _finite_array(values, "values", ndim=1)
    terminal_array = np.asarray(terminals)
    if rewards_array.shape != values_array.shape or terminal_array.shape != rewards_array.shape:
        raise PPOContractError("GAE sequence lengths disagree")
    if terminal_array.dtype != np.bool_:
        raise PPOContractError("GAE terminals must be boolean")
    if isinstance(next_value, bool) or not math.isfinite(float(next_value)):
        raise PPOContractError("GAE next value must be finite")
    advantages = np.zeros_like(rewards_array)
    following_value = float(next_value)
    following_advantage = 0.0
    gamma = PPO_TRAINING_CONTRACT.discount_factor
    gae_lambda = PPO_TRAINING_CONTRACT.gae_lambda
    for index in range(len(rewards_array) - 1, -1, -1):
        continuation = 0.0 if terminal_array[index] else 1.0
        delta = rewards_array[index] + gamma * following_value * continuation - values_array[index]
        following_advantage = delta + gamma * gae_lambda * continuation * following_advantage
        advantages[index] = following_advantage
        following_value = values_array[index]
    return advantages, advantages + values_array


class PPOOptimizer:
    """Manual clipped-PPO backpropagation with deterministic Adam minibatches."""

    def __init__(self, model: PPOActorCritic, training_run: PPOTrainingRun):
        if not isinstance(model, PPOActorCritic):
            raise TypeError("model must be PPOActorCritic")
        if not isinstance(training_run, PPOTrainingRun):
            raise TypeError("training_run must be PPOTrainingRun")
        if model.training_run_sha256 != training_run.sha256:
            raise PPOContractError("PPO optimizer training-run provenance mismatch")
        self.model = model
        self._rng = np.random.default_rng(
            _seed64(training_run.learner_seed_hex, "minibatches")
        )
        self._first = {name: np.zeros_like(value) for name, value in model.parameters.items()}
        self._second = {name: np.zeros_like(value) for name, value in model.parameters.items()}
        self._steps = 0

    def minibatches(self) -> Iterator[np.ndarray]:
        contract = PPO_TRAINING_CONTRACT
        size = contract.rollout_batch_size
        for _ in range(contract.update_epochs):
            order = self._rng.permutation(size)
            for start in range(0, size, contract.minibatch_size):
                yield order[start : start + contract.minibatch_size]

    def loss_and_gradients(self, batch: PPOBatch) -> tuple[PPOLoss, dict[str, np.ndarray]]:
        batch = batch.validated()
        probabilities, values, cache = self.model._forward_arrays(
            batch.observations, batch.action_masks
        )
        observations, hidden1, hidden2, masks = cache
        size = len(batch.action_indices)
        rows = np.arange(size)
        selected = probabilities[rows, batch.action_indices]
        if np.any(selected <= 0.0):
            raise PPOContractError("selected PPO action has zero model probability")
        log_probabilities = np.log(selected)
        ratios = np.exp(log_probabilities - batch.old_log_probabilities)
        clip = PPO_TRAINING_CONTRACT.policy_clip
        unclipped = ratios * batch.advantages
        clipped_ratios = np.clip(ratios, 1.0 - clip, 1.0 + clip)
        clipped = clipped_ratios * batch.advantages
        policy_loss = -float(np.mean(np.minimum(unclipped, clipped)))

        active_policy = unclipped <= clipped
        log_probability_gradient = np.where(
            active_policy, -batch.advantages * ratios / size, 0.0
        )
        logits_gradient = -probabilities * log_probability_gradient[:, None]
        logits_gradient[rows, batch.action_indices] += log_probability_gradient

        safe_probabilities = np.where(masks, probabilities, 1.0)
        log_all = np.where(masks, np.log(safe_probabilities), 0.0)
        entropy_rows = -np.sum(np.where(masks, probabilities * log_all, 0.0), axis=1)
        entropy = float(np.mean(entropy_rows))
        mean_log = np.sum(probabilities * log_all, axis=1, keepdims=True)
        entropy_gradient = (
            PPO_TRAINING_CONTRACT.entropy_coefficient
            * probabilities
            * (log_all - mean_log)
            / size
        )
        logits_gradient += np.where(masks, entropy_gradient, 0.0)

        value_delta = values - batch.returns
        value_clip = PPO_TRAINING_CONTRACT.value_clip
        clipped_values = batch.old_values + np.clip(
            values - batch.old_values, -value_clip, value_clip
        )
        clipped_delta = clipped_values - batch.returns
        raw_squared = value_delta * value_delta
        clipped_squared = clipped_delta * clipped_delta
        use_raw = raw_squared >= clipped_squared
        value_loss = 0.5 * float(np.mean(np.maximum(raw_squared, clipped_squared)))
        within_clip = np.abs(values - batch.old_values) <= value_clip
        value_gradient = np.where(
            use_raw,
            value_delta,
            np.where(within_clip, clipped_delta, 0.0),
        )
        value_gradient *= PPO_TRAINING_CONTRACT.value_coefficient / size

        p = self.model.parameters
        gradients: dict[str, np.ndarray] = {}
        gradients["policy_w"] = hidden2.T @ logits_gradient
        gradients["policy_b"] = np.sum(logits_gradient, axis=0)
        gradients["value_w"] = hidden2.T @ value_gradient[:, None]
        gradients["value_b"] = np.asarray([np.sum(value_gradient)])
        hidden2_gradient = (
            logits_gradient @ p["policy_w"].T
            + value_gradient[:, None] @ p["value_w"].T
        )
        pre2_gradient = hidden2_gradient * (1.0 - hidden2 * hidden2)
        gradients["w2"] = hidden1.T @ pre2_gradient
        gradients["b2"] = np.sum(pre2_gradient, axis=0)
        hidden1_gradient = pre2_gradient @ p["w2"].T
        pre1_gradient = hidden1_gradient * (1.0 - hidden1 * hidden1)
        gradients["w1"] = observations.T @ pre1_gradient
        gradients["b1"] = np.sum(pre1_gradient, axis=0)

        total = (
            policy_loss
            + PPO_TRAINING_CONTRACT.value_coefficient * value_loss
            - PPO_TRAINING_CONTRACT.entropy_coefficient * entropy
        )
        return PPOLoss(total, policy_loss, value_loss, entropy), gradients

    def apply_gradients(
        self, loss: PPOLoss, gradients: dict[str, np.ndarray]
    ) -> PPOLoss:
        if set(gradients) != set(_PARAMETER_ORDER):
            raise PPOContractError("PPO gradients do not match model parameters")
        for name in _PARAMETER_ORDER:
            gradient = np.asarray(gradients[name])
            if gradient.shape != self.model.parameters[name].shape:
                raise PPOContractError("PPO gradient shape does not match its parameter")
            if not np.all(np.isfinite(gradient)):
                raise PPOContractError("PPO gradients must be finite")
        squared_norm = sum(float(np.sum(value * value)) for value in gradients.values())
        norm = math.sqrt(squared_norm)
        maximum = PPO_TRAINING_CONTRACT.maximum_gradient_norm
        scale = min(1.0, maximum / norm) if norm > 0.0 else 1.0
        self._steps += 1
        rate = PPO_TRAINING_CONTRACT.learning_rate
        for name in _PARAMETER_ORDER:
            gradient = gradients[name] * scale
            self._first[name] = ADAM_BETA1 * self._first[name] + (1.0 - ADAM_BETA1) * gradient
            self._second[name] = ADAM_BETA2 * self._second[name] + (1.0 - ADAM_BETA2) * gradient * gradient
            first_hat = self._first[name] / (1.0 - ADAM_BETA1**self._steps)
            second_hat = self._second[name] / (1.0 - ADAM_BETA2**self._steps)
            self.model.parameters[name] -= rate * first_hat / (np.sqrt(second_hat) + ADAM_EPSILON)
        return PPOLoss(
            loss.total,
            loss.policy,
            loss.value,
            loss.entropy,
            unclipped_gradient_norm=norm,
            applied_gradient_norm=min(norm, maximum),
        )

    def step(self, batch: PPOBatch) -> PPOLoss:
        loss, gradients = self.loss_and_gradients(batch)
        return self.apply_gradients(loss, gradients)

    def update(self, batch: PPOBatch) -> tuple[PPOLoss, ...]:
        batch = batch.validated(expected_size=PPO_TRAINING_CONTRACT.rollout_batch_size)
        return tuple(self.step(batch.take(indices)) for indices in self.minibatches())
