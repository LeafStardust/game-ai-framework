"""Frozen one-batch advantage-normalization shadow for progress-reward PPO."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

import numpy as np

from games.balatro.env.ppo_contract import PPOContractError
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_model import PPOActorCritic, PPOBatch, PPOLoss


PPO_PROGRESS_ADVANTAGE_NORMALIZATION_SHADOW_SCHEMA = (
    "balatro-red-white-progress-advantage-normalization-shadow-v1"
)


@dataclass(frozen=True)
class PPOProgressNormalizedUpdate:
    source_advantage_mean: float
    source_advantage_variance: float
    source_advantage_standard_deviation: float
    normalized_advantage_mean: float
    normalized_advantage_variance: float
    initial_policy_parameter_sha256: str
    unnormalized_policy_parameter_sha256: str
    normalized_policy_parameter_sha256: str
    unnormalized_losses: tuple[PPOLoss, ...]
    normalized_losses: tuple[PPOLoss, ...]
    normalized_model: PPOActorCritic

    def __post_init__(self) -> None:
        numbers = (
            self.source_advantage_mean,
            self.source_advantage_variance,
            self.source_advantage_standard_deviation,
            self.normalized_advantage_mean,
            self.normalized_advantage_variance,
        )
        if any(not math.isfinite(value) for value in numbers):
            raise PPOContractError("normalized shadow statistics are nonfinite")
        if (
            self.source_advantage_variance <= 0.0
            or self.source_advantage_standard_deviation <= 0.0
            or abs(self.normalized_advantage_mean) > 1e-12
            or not math.isclose(
                self.normalized_advantage_variance,
                1.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise PPOContractError("normalized shadow statistics drifted")
        for digest in (
            self.initial_policy_parameter_sha256,
            self.unnormalized_policy_parameter_sha256,
            self.normalized_policy_parameter_sha256,
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise PPOContractError("normalized shadow policy digest is invalid")
        if (
            len(self.unnormalized_losses) != 80
            or len(self.normalized_losses) != 80
            or not isinstance(self.normalized_model, PPOActorCritic)
        ):
            raise PPOContractError("normalized shadow optimizer evidence is incomplete")


def normalize_ppo_batch_advantages(
    batch: PPOBatch,
) -> tuple[PPOBatch, dict[str, float]]:
    """Return one detached batch with only advantages centered and scaled."""

    if not isinstance(batch, PPOBatch):
        raise TypeError("normalized shadow requires PPOBatch")
    source = batch.validated(expected_size=2048)
    advantages = np.asarray(source.advantages, dtype=np.float64)
    mean = float(np.mean(advantages))
    variance = float(np.mean((advantages - mean) ** 2))
    deviation = math.sqrt(variance)
    if not math.isfinite(deviation) or deviation <= 0.0:
        raise PPOContractError("normalized shadow advantage variance is invalid")
    normalized = (advantages - mean) / deviation
    shadow = replace(source, advantages=normalized).validated(expected_size=2048)
    return shadow, {
        "source_mean": mean,
        "source_variance": variance,
        "source_standard_deviation": deviation,
        "normalized_mean": float(np.mean(normalized)),
        "normalized_variance": float(np.mean(normalized * normalized)),
    }


def run_normalized_advantage_shadow_update(
    initial_learner: PPOLearner,
    batch: PPOBatch,
    *,
    expected_unnormalized_policy_sha256: str,
) -> PPOProgressNormalizedUpdate:
    """Apply exact source and normalized updates to independent learner clones."""

    if not isinstance(initial_learner, PPOLearner):
        raise TypeError("normalized shadow requires PPOLearner")
    initial_payload = initial_learner.serialize()
    initial_digest = initial_learner.model.parameter_sha256
    normalized_batch, statistics = normalize_ppo_batch_advantages(batch)
    source_batch = batch.validated(expected_size=2048)

    unnormalized = PPOLearner.restore(initial_learner.training_run, initial_payload)
    normalized = PPOLearner.restore(initial_learner.training_run, initial_payload)
    unnormalized_losses = unnormalized.optimizer.update(source_batch)
    normalized_losses = normalized.optimizer.update(normalized_batch)
    if initial_learner.serialize() != initial_payload:
        raise PPOContractError("normalized shadow mutated its initial learner")
    if unnormalized.model.parameter_sha256 != expected_unnormalized_policy_sha256:
        raise PPOContractError("normalized shadow source policy reproduction drifted")
    return PPOProgressNormalizedUpdate(
        statistics["source_mean"],
        statistics["source_variance"],
        statistics["source_standard_deviation"],
        statistics["normalized_mean"],
        statistics["normalized_variance"],
        initial_digest,
        unnormalized.model.parameter_sha256,
        normalized.model.parameter_sha256,
        unnormalized_losses,
        normalized_losses,
        normalized.model,
    )
