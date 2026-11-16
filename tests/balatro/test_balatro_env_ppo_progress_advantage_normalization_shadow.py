import numpy as np
import pytest

from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_model import PPOBatch
from games.balatro.env.ppo_progress_advantage_normalization_shadow import (
    normalize_ppo_batch_advantages,
    run_normalized_advantage_shadow_update,
)


def _batch(learner, *, constant=False):
    size = PPO_PROGRESS_TRAINING_CONTRACT.rollout_batch_size
    observations = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.observation_size), dtype=np.float64
    )
    observations[:, 0] = np.linspace(-1.0, 1.0, size)
    masks = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.action_size), dtype=np.bool_
    )
    masks[:, (0, 4)] = True
    actions = np.resize(np.asarray([0, 4], dtype=np.int64), size)
    probabilities, values, _ = learner.model.evaluate_batch(observations, masks)
    advantages = (
        np.ones(size, dtype=np.float64)
        if constant
        else np.linspace(-3.0, 1.0, size, dtype=np.float64)
    )
    return PPOBatch(
        observations,
        masks,
        actions,
        np.repeat(np.arange(8, dtype=np.int64), size // 8),
        np.tile(np.arange(size // 8, dtype=np.int64), 8),
        np.log(probabilities[np.arange(size), actions]),
        values,
        advantages,
        values + advantages,
    )


def test_normalized_shadow_changes_only_advantages_and_centers_exact_batch():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-BATCH", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    learner = PPOLearner(run)
    source = _batch(learner)

    normalized, statistics = normalize_ppo_batch_advantages(source)

    assert statistics["source_mean"] == pytest.approx(-1.0)
    assert statistics["normalized_mean"] == pytest.approx(0.0, abs=1e-15)
    assert statistics["normalized_variance"] == pytest.approx(1.0)
    for name in (
        "observations",
        "action_masks",
        "action_indices",
        "episode_indices",
        "decision_indices",
        "old_log_probabilities",
        "old_values",
        "returns",
    ):
        assert np.array_equal(getattr(normalized, name), getattr(source, name))
    assert not np.array_equal(normalized.advantages, source.advantages)


def test_normalized_shadow_reproduces_source_and_keeps_initial_immutable():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-UPDATE", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOLearner(run)
    batch = _batch(initial)
    source = PPOLearner.restore(run, initial.serialize())
    source.optimizer.update(batch)
    initial_payload = initial.serialize()

    result = run_normalized_advantage_shadow_update(
        initial,
        batch,
        expected_unnormalized_policy_sha256=source.model.parameter_sha256,
    )

    assert initial.serialize() == initial_payload
    assert result.unnormalized_policy_parameter_sha256 == source.model.parameter_sha256
    assert result.normalized_policy_parameter_sha256 != result.unnormalized_policy_parameter_sha256
    assert result.normalized_advantage_mean == pytest.approx(0.0, abs=1e-15)
    assert result.normalized_advantage_variance == pytest.approx(1.0)


def test_normalized_shadow_rejects_zero_variance_and_source_drift():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-REJECT", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    learner = PPOLearner(run)
    with pytest.raises(PPOContractError, match="variance is invalid"):
        normalize_ppo_batch_advantages(_batch(learner, constant=True))

    with pytest.raises(PPOContractError, match="source policy reproduction drifted"):
        run_normalized_advantage_shadow_update(
            learner,
            _batch(learner),
            expected_unnormalized_policy_sha256="f" * 64,
        )
