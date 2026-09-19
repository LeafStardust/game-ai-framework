import math

import numpy as np
import pytest

from games.balatro.env.action_encoding import ActionMask, PUBLIC_ACTION_VERSION
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_VERSION,
    EncodedPublicObservation,
)
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import (
    ADAM_BETA1,
    ADAM_BETA2,
    ADAM_EPSILON,
    PPO_MODEL_VERSION,
    PPO_OPTIMIZER_VERSION,
    PPOActorCritic,
    PPOBatch,
    PPOOptimizer,
    compute_gae,
)


def _model(seed="MODEL"):
    run = PPOTrainingRun.from_seed(seed)
    return run, PPOActorCritic(run)


def _small_batch(model):
    size = 2
    observations = np.zeros(
        (size, PPO_TRAINING_CONTRACT.observation_size), dtype=np.float64
    )
    observations[1, 0] = 1.0
    masks = np.zeros(
        (size, PPO_TRAINING_CONTRACT.action_size), dtype=np.bool_
    )
    masks[:, (0, 3)] = True
    actions = np.asarray([0, 3], dtype=np.int64)
    probabilities, values, _ = model.evaluate_batch(observations, masks)
    return PPOBatch(
        observations=observations,
        action_masks=masks,
        action_indices=actions,
        episode_indices=np.asarray([0, 0], dtype=np.int64),
        decision_indices=np.asarray([0, 1], dtype=np.int64),
        old_log_probabilities=np.log(probabilities[np.arange(size), actions]),
        old_values=values.copy(),
        advantages=np.asarray([1.0, -0.5]),
        returns=np.asarray([0.75, -0.25]),
    )


def test_env_ppo_model_initialization_is_seeded_and_contract_shaped():
    _, first = _model("SAME")
    _, second = _model("SAME")
    _, different = _model("DIFFERENT")

    assert first.parameter_sha256 == second.parameter_sha256
    assert first.parameter_sha256 != different.parameter_sha256
    assert PPO_MODEL_VERSION == "balatro-red-white-ppo-actor-critic-v1"
    assert PPO_OPTIMIZER_VERSION == "balatro-red-white-ppo-adam-v1"
    assert (ADAM_BETA1, ADAM_BETA2, ADAM_EPSILON) == (0.9, 0.999, 1e-8)
    assert first.parameters["w1"].shape == (2456, 512)
    assert first.parameters["w2"].shape == (512, 256)
    assert first.parameters["policy_w"].shape == (256, 27)
    assert first.parameters["value_w"].shape == (256, 1)


def test_env_ppo_model_inference_masks_logits_and_returns_value_exactly():
    _, model = _model()
    observation = EncodedPublicObservation(
        PUBLIC_OBSERVATION_VERSION,
        (0.0,) * PPO_TRAINING_CONTRACT.observation_size,
    )
    mask_values = [False] * PPO_TRAINING_CONTRACT.action_size
    mask_values[0] = mask_values[3] = True
    mask = ActionMask(PUBLIC_ACTION_VERSION, tuple(mask_values))

    output = model.infer(observation, mask)

    assert output.probabilities[0] == pytest.approx(0.5)
    assert output.probabilities[3] == pytest.approx(0.5)
    assert sum(output.probabilities) == pytest.approx(1.0)
    assert all(
        probability == 0.0
        for index, probability in enumerate(output.probabilities)
        if index not in {0, 3}
    )
    assert output.value_estimate == 0.0


def test_env_ppo_model_empty_mask_and_shape_drift_fail_closed():
    _, model = _model()
    observations = np.zeros((1, PPO_TRAINING_CONTRACT.observation_size))

    with pytest.raises(PPOContractError, match="empty action mask"):
        model.evaluate_batch(
            observations,
            np.zeros((1, PPO_TRAINING_CONTRACT.action_size), dtype=np.bool_),
        )
    with pytest.raises(PPOContractError, match="observation shape"):
        model.evaluate_batch(
            np.zeros((1, 1)),
            np.ones((1, PPO_TRAINING_CONTRACT.action_size), dtype=np.bool_),
        )


def test_env_ppo_gae_uses_frozen_gamma_lambda_and_terminal_cutoff():
    advantages, returns = compute_gae(
        [0.0, 0.0, 1.0],
        [0.1, 0.2, 0.3],
        np.asarray([False, False, True], dtype=np.bool_),
    )

    assert advantages == pytest.approx([0.808406675, 0.75535, 0.7])
    assert returns == pytest.approx([0.908406675, 0.95535, 1.0])


def test_env_ppo_optimizer_gradient_matches_finite_difference():
    run, model = _model("GRADIENT")
    optimizer = PPOOptimizer(model, run)
    batch = _small_batch(model)
    loss, gradients = optimizer.loss_and_gradients(batch)
    epsilon = 1e-6
    parameter = model.parameters["policy_b"]
    original = float(parameter[0])
    parameter[0] = original + epsilon
    plus, _ = optimizer.loss_and_gradients(batch)
    parameter[0] = original - epsilon
    minus, _ = optimizer.loss_and_gradients(batch)
    parameter[0] = original

    numerical = (plus.total - minus.total) / (2.0 * epsilon)
    assert math.isfinite(loss.total)
    assert gradients["policy_b"][0] == pytest.approx(
        numerical, rel=1e-5, abs=1e-7
    )


def test_env_ppo_optimizer_step_is_deterministic_and_clips_global_norm():
    first_run, first_model = _model("STEP")
    second_run, second_model = _model("STEP")
    first = PPOOptimizer(first_model, first_run)
    second = PPOOptimizer(second_model, second_run)
    before = first_model.parameter_sha256

    first_loss = first.step(_small_batch(first_model))
    second_loss = second.step(_small_batch(second_model))

    assert first_model.parameter_sha256 != before
    assert first_model.parameter_sha256 == second_model.parameter_sha256
    assert first_loss == second_loss
    assert first_loss.unclipped_gradient_norm is not None
    assert first_loss.applied_gradient_norm == pytest.approx(
        min(first_loss.unclipped_gradient_norm, 0.5)
    )


def test_env_ppo_minibatch_schedule_is_complete_and_seeded():
    first_run, first_model = _model("SCHEDULE")
    second_run, second_model = _model("SCHEDULE")
    first = list(PPOOptimizer(first_model, first_run).minibatches())
    second = list(PPOOptimizer(second_model, second_run).minibatches())

    assert len(first) == 80
    assert all(len(indices) == 256 for indices in first)
    assert all(np.array_equal(left, right) for left, right in zip(first, second))
    for epoch in range(10):
        combined = np.concatenate(first[epoch * 8 : (epoch + 1) * 8])
        assert sorted(combined.tolist()) == list(range(2048))


def test_env_ppo_batch_rejects_illegal_selected_action():
    _, model = _model("BAD-BATCH")
    batch = _small_batch(model)
    batch.action_masks[0, 0] = False

    with pytest.raises(PPOContractError, match="illegal selected action"):
        batch.validated()


def test_env_ppo_optimizer_rejects_mismatched_run_and_nonfinite_gradient():
    first_run, model = _model("FIRST")
    second_run = PPOTrainingRun.from_seed("SECOND")
    with pytest.raises(PPOContractError, match="provenance mismatch"):
        PPOOptimizer(model, second_run)

    optimizer = PPOOptimizer(model, first_run)
    loss, gradients = optimizer.loss_and_gradients(_small_batch(model))
    gradients["policy_b"][0] = np.nan
    with pytest.raises(PPOContractError, match="gradients must be finite"):
        optimizer.apply_gradients(loss, gradients)
