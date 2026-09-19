from copy import deepcopy

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
from games.balatro.env.ppo_batch import (
    PPO_BATCH_ASSEMBLER_VERSION,
    PPOBatchAssembler,
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
from games.balatro.env.seeded_evaluation import EVALUATION_MODE
from games.balatro.env.state import RunStatus, TurnOwner


def _episode(run, episode_index, *, length=257):
    action = EnvAction.from_alias("SELECT_BLIND")
    selected = action_index(action)
    mask_values = [False] * PPO_TRAINING_CONTRACT.action_size
    mask_values[selected] = True
    mask = ActionMask(PUBLIC_ACTION_VERSION, tuple(mask_values))
    probabilities = tuple(1.0 if index == selected else 0.0 for index in range(27))
    observation_values = [0.0] * PPO_TRAINING_CONTRACT.observation_size
    observation_values[0] = float(episode_index % 8)
    observation = EncodedPublicObservation(
        PUBLIC_OBSERVATION_VERSION, tuple(observation_values)
    )
    boundary = PPORolloutBoundary(
        observation=observation,
        deck="RED",
        stake="WHITE",
        mode=EVALUATION_MODE,
        phase="BLIND_SELECT",
        status=RunStatus.RUNNING,
        owner=TurnOwner.AGENT,
        ante=1,
        money=4,
        score=0.0,
        blind_requirement=300.0,
    )
    final = PPORolloutBoundary(
        observation=None,
        deck="RED",
        stake="WHITE",
        mode=EVALUATION_MODE,
        phase="GAME_OVER",
        status=RunStatus.LOSS,
        owner=TurnOwner.TERMINAL,
        ante=1,
        money=4,
        score=0.0,
        blind_requirement=300.0,
    )
    decisions = tuple(
        PPORolloutDecision(
            training_run_sha256=run.sha256,
            episode_index=episode_index,
            decision_index=index,
            observation=observation,
            action_mask=mask,
            probabilities=probabilities,
            value_estimate=float(episode_index % 8) + index / 1000.0,
            action_index=selected,
            action=action,
        )
        for index in range(length)
    )
    rewards = (0.0,) * (length - 1) + (-1.0,)
    return PPORolloutEpisode(
        schema_version=PPO_ROLLOUT_EPISODE_SCHEMA,
        training_run=run,
        episode_index=episode_index,
        game_seed=run.game_seed(episode_index),
        boundaries=(boundary,) * length + (final,),
        decisions=decisions,
        rewards=rewards,
    )


def test_env_ppo_batch_assembles_exact_stream_slices_and_restores_carryover():
    run = PPOTrainingRun.from_seed("BATCH")
    assembler = PPOBatchAssembler(run)
    for episode_index in range(8):
        assembler.add_episode(_episode(run, episode_index))

    assert PPO_BATCH_ASSEMBLER_VERSION == "balatro-red-white-ppo-batch-assembler-v1"
    assert assembler.ready is True
    assert assembler.next_episode_indices == tuple(range(8, 16))
    batch = assembler.assemble()

    assert batch.observations.shape == (2048, 2456)
    assert batch.action_masks.shape == (2048, 27)
    assert batch.action_indices.shape == (2048,)
    assert batch.episode_indices.tolist() == [
        stream for stream in range(8) for _ in range(256)
    ]
    assert batch.decision_indices.tolist() == [
        decision for _ in range(8) for decision in range(256)
    ]
    assert batch.observations[:, 0].tolist() == [
        float(stream) for stream in range(8) for _ in range(256)
    ]
    assert np.allclose(batch.returns, batch.advantages + batch.old_values)
    assert assembler.carryover_counts == (1,) * 8
    assert assembler.ready is False

    snapshot = assembler.serialize()
    restored = PPOBatchAssembler.restore(run, snapshot)
    assert restored.serialize() == snapshot
    assert restored.carryover_counts == (1,) * 8
    assert restored.next_episode_indices == tuple(range(8, 16))


def test_env_ppo_batch_requires_every_stream_and_exact_episode_order():
    run = PPOTrainingRun.from_seed("ORDER")
    assembler = PPOBatchAssembler(run)
    assembler.add_episode(_episode(run, 0, length=1))

    with pytest.raises(PPOContractError, match="insufficient stream transitions"):
        assembler.assemble()
    with pytest.raises(PPOContractError, match="out of stream order"):
        assembler.add_episode(_episode(run, 0, length=1))
    with pytest.raises(PPOContractError, match="out of stream order"):
        PPOBatchAssembler(run).add_episode(_episode(run, 8, length=1))


def test_env_ppo_batch_computes_gae_separately_at_each_episode_terminal():
    run = PPOTrainingRun.from_seed("EPISODE-GAE")
    assembler = PPOBatchAssembler(run)
    assembler.add_episode(_episode(run, 0, length=1))
    assembler.add_episode(_episode(run, 8, length=1))

    queued = assembler.serialize()["streams"][0]
    assert [item["episode_index"] for item in queued] == [0, 8]
    assert [item["decision_index"] for item in queued] == [0, 0]
    assert [item["advantage"] for item in queued] == pytest.approx([-1.0, -1.0])
    assert [item["return_value"] for item in queued] == pytest.approx([-1.0, -1.0])


def test_env_ppo_batch_rejects_cross_run_episode_and_tampered_carryover():
    run = PPOTrainingRun.from_seed("OWNER")
    other = PPOTrainingRun.from_seed("OTHER")
    assembler = PPOBatchAssembler(run)
    with pytest.raises(PPOContractError, match="training-run provenance"):
        assembler.add_episode(_episode(other, 0, length=1))

    assembler.add_episode(_episode(run, 0, length=1))
    snapshot = assembler.serialize()
    tampered = deepcopy(snapshot)
    tampered["streams"][0][0]["action_mask"] = [False] * 27
    with pytest.raises(PPOContractError, match="action mask is malformed"):
        PPOBatchAssembler.restore(run, tampered)

    wrong_indices = deepcopy(snapshot)
    wrong_indices["next_episode_indices"][0] = 9
    with pytest.raises(PPOContractError, match="next episode index is invalid"):
        PPOBatchAssembler.restore(run, wrong_indices)

    wrong_stream = deepcopy(snapshot)
    wrong_stream["streams"][0][0]["episode_index"] = 1
    with pytest.raises(PPOContractError, match="stream provenance is invalid"):
        PPOBatchAssembler.restore(run, wrong_stream)
