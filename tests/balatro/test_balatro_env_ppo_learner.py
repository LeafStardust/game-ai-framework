import numpy as np
import pytest

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_VERSION,
    ActionMask,
    action_index,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_VERSION,
    EncodedPublicObservation,
)
from games.balatro.env.ppo_contract import (
    PPO_ROLLOUT_EPISODE_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutBoundary,
    PPORolloutDecision,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import (
    PPO_LEARNER_CHECKPOINT_VERSION,
    PPOLearner,
)
from games.balatro.env.ppo_model import PPOBatch
from games.balatro.env.seeded_evaluation import EVALUATION_MODE
from games.balatro.env.state import RunStatus, TurnOwner


def _small_batch(learner):
    size = 2
    observations = np.zeros(
        (size, PPO_TRAINING_CONTRACT.observation_size), dtype=np.float64
    )
    observations[1, 0] = 1.0
    masks = np.zeros((size, PPO_TRAINING_CONTRACT.action_size), dtype=np.bool_)
    masks[:, (0, 3)] = True
    actions = np.asarray([0, 3], dtype=np.int64)
    probabilities, values, _ = learner.model.evaluate_batch(observations, masks)
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


def _one_transition_episode(run):
    action = EnvAction.from_alias("SELECT_BLIND")
    selected = action_index(action)
    mask_values = [False] * PPO_TRAINING_CONTRACT.action_size
    mask_values[selected] = True
    mask = ActionMask(PUBLIC_ACTION_VERSION, tuple(mask_values))
    observation = EncodedPublicObservation(
        PUBLIC_OBSERVATION_VERSION,
        (0.0,) * PPO_TRAINING_CONTRACT.observation_size,
    )
    start = PPORolloutBoundary(
        observation, "RED", "WHITE", EVALUATION_MODE, "BLIND_SELECT",
        RunStatus.RUNNING, TurnOwner.AGENT, 1, 4, 0.0, 300.0,
    )
    final = PPORolloutBoundary(
        None, "RED", "WHITE", EVALUATION_MODE, "GAME_OVER",
        RunStatus.LOSS, TurnOwner.TERMINAL, 1, 4, 0.0, 300.0,
    )
    probabilities = tuple(
        1.0 if index == selected else 0.0
        for index in range(PPO_TRAINING_CONTRACT.action_size)
    )
    decision = PPORolloutDecision(
        run.sha256, 0, 0, observation, mask, probabilities, 0.0, selected, action
    )
    return PPORolloutEpisode(
        PPO_ROLLOUT_EPISODE_SCHEMA,
        run,
        0,
        run.game_seed(0),
        (start, final),
        (decision,),
        (-1.0,),
    )


@pytest.fixture(scope="module")
def checkpoint():
    run = PPOTrainingRun.from_seed("LEARNER-CHECKPOINT")
    learner = PPOLearner(run)
    return run, learner.serialize()


def test_env_ppo_learner_checkpoint_round_trips_every_owned_state(checkpoint):
    run, payload = checkpoint
    restored = PPOLearner.restore(run, payload)

    assert PPO_LEARNER_CHECKPOINT_VERSION == (
        "balatro-red-white-ppo-learner-checkpoint-v1"
    )
    assert restored.serialize() == payload
    assert restored.model.parameter_sha256 == PPOLearner(run).model.parameter_sha256
    assert restored.completed_batch_count == 0
    assert restored.total_consumed_environment_transitions == 0


def test_env_ppo_learner_checkpoint_owns_carryover_indices_and_transition_count():
    run = PPOTrainingRun.from_seed("LEARNER-CARRYOVER")
    learner = PPOLearner(run)
    learner.add_episode(_one_transition_episode(run))

    restored = PPOLearner.restore(run, learner.serialize())

    assert restored.assembler.carryover_counts == (1, 0, 0, 0, 0, 0, 0, 0)
    assert restored.assembler.next_episode_indices == (8, 1, 2, 3, 4, 5, 6, 7)
    assert restored.total_consumed_environment_transitions == 1


def test_env_ppo_learner_restore_is_exact_across_next_optimizer_step(checkpoint):
    run, payload = checkpoint
    uninterrupted = PPOLearner(run)
    restored = PPOLearner.restore(run, payload)

    assert np.array_equal(
        next(uninterrupted.optimizer.minibatches()),
        next(restored.optimizer.minibatches()),
    )
    left_loss = uninterrupted.optimizer.step(_small_batch(uninterrupted))
    right_loss = restored.optimizer.step(_small_batch(restored))

    assert left_loss == right_loss
    assert uninterrupted.model.parameter_sha256 == restored.model.parameter_sha256
    for name in uninterrupted.model.parameters:
        assert np.array_equal(
            uninterrupted.optimizer._first[name], restored.optimizer._first[name]
        )
        assert np.array_equal(
            uninterrupted.optimizer._second[name], restored.optimizer._second[name]
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", "wrong", "checkpoint version"),
        ("model_version", "wrong", "model version"),
        ("optimizer_version", "wrong", "optimizer version"),
        ("assembler_version", "wrong", "assembler version"),
        ("completed_batch_count", True, "nonnegative exact integer"),
        ("total_consumed_environment_transitions", 1, "transition counter"),
        ("adam_step", 1, "optimizer-step counter"),
    ],
)
def test_env_ppo_learner_rejects_version_and_counter_drift(
    checkpoint, field, value, message
):
    run, payload = checkpoint
    tampered = dict(payload)
    tampered[field] = value

    with pytest.raises(PPOContractError, match=message):
        PPOLearner.restore(run, tampered)


def test_env_ppo_learner_rejects_run_shape_digest_and_nonfinite_drift(checkpoint):
    run, payload = checkpoint
    with pytest.raises(PPOContractError, match="training-run provenance"):
        PPOLearner.restore(PPOTrainingRun.from_seed("OTHER"), payload)

    bad_shape = dict(payload)
    bad_shape["parameters"] = dict(payload["parameters"])
    bad_shape["parameters"]["b1"] = dict(payload["parameters"]["b1"])
    bad_shape["parameters"]["b1"]["shape"] = [1]
    with pytest.raises(PPOContractError, match="shape or dtype"):
        PPOLearner.restore(run, bad_shape)

    bad_digest = dict(payload)
    bad_digest["adam_first_moments"] = dict(payload["adam_first_moments"])
    bad_digest["adam_first_moments"]["b1"] = dict(
        payload["adam_first_moments"]["b1"]
    )
    bad_digest["adam_first_moments"]["b1"]["sha256"] = "0" * 64
    with pytest.raises(PPOContractError, match="digest is invalid"):
        PPOLearner.restore(run, bad_digest)

    learner = PPOLearner(run)
    learner.model.parameters["b1"][0] = np.nan
    with pytest.raises(PPOContractError, match="arrays must be finite"):
        learner.serialize()


def test_env_ppo_learner_rejects_schema_and_rng_state_drift(checkpoint):
    run, payload = checkpoint
    missing = dict(payload)
    del missing["parameters"]
    with pytest.raises(PPOContractError, match="fields are incomplete"):
        PPOLearner.restore(run, missing)

    bad_rng = dict(payload)
    bad_rng["minibatch_rng_state"] = {"bit_generator": "invalid"}
    with pytest.raises(PPOContractError, match="RNG state"):
        PPOLearner.restore(run, bad_rng)
