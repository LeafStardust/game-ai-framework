from dataclasses import replace
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic, PPOBatch
from games.balatro.env.ppo_progress_study import PPOProgressStudyEpisodeRecord
from games.balatro.env.ppo_progress_study_optimizer_attribution import (
    _expected_post_batch_hashes,
    run_progress_study_optimizer_attribution,
    shapley_policy_margin_attribution,
    summarize_optimizer_batch,
)


def _batch(model):
    size = PPO_PROGRESS_TRAINING_CONTRACT.rollout_batch_size
    observations = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.observation_size), dtype=np.float64
    )
    masks = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.action_size), dtype=np.bool_
    )
    masks[:, (0, 4)] = True
    actions = np.resize(np.asarray([0, 4], dtype=np.int64), size)
    probabilities, values, _ = model.evaluate_batch(observations, masks)
    advantages = np.resize(np.asarray([-1.0, 2.0], dtype=np.float64), size)
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


def _record(batch, digest):
    return PPOProgressStudyEpisodeRecord(
        "a" * 64,
        batch,
        f"SEED-{batch}",
        "LOSS",
        1,
        batch,
        batch,
        digest,
        (-1.0,),
        (-1.0,),
    )


def test_optimizer_attribution_summarizes_exact_implicated_shop_signal():
    run = PPOTrainingRun.from_seed(
        "OPTIMIZER-ATTRIBUTION", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    model = PPOActorCritic(run)

    summary = summarize_optimizer_batch(_batch(model), model, 1)

    assert summary["transition_count"] == 2048
    assert summary["episode_count"] == 8
    assert summary["action_slots"][0]["selected_count"] == 1024
    assert summary["action_slots"][4]["selected_count"] == 1024
    implicated = summary["implicated_shop_legal_set"]
    assert implicated["transition_count"] == 2048
    assert implicated["advantages"]["negative_count"] == 1024
    assert implicated["advantages"]["positive_count"] == 1024
    assert implicated["first_step_voucher_minus_end_policy_signal"] > 0.0
    assert [group["selected_action_index"] for group in implicated["selected_action_groups"]] == [0, 4]


def test_optimizer_attribution_requires_all_eight_stable_post_batch_hashes():
    records = tuple(_record(batch, f"{batch:064x}") for batch in range(1, 9))
    assert _expected_post_batch_hashes(records) == {
        batch: f"{batch:064x}" for batch in range(1, 9)
    }

    with pytest.raises(PPOContractError, match="policy hash drifted"):
        _expected_post_batch_hashes(
            records + (replace(records[-1], policy_parameter_sha256_after_commit="f" * 64),)
        )
    with pytest.raises(PPOContractError, match="batches are incomplete"):
        _expected_post_batch_hashes(records[:-1])


def test_optimizer_attribution_shapley_partition_closes_exact_policy_margin():
    run = PPOTrainingRun.from_seed(
        "OPTIMIZER-SHAPLEY", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOActorCritic(run)
    candidate = deepcopy(initial)
    candidate.parameters["policy_b"][4] += 0.75
    mask = [False] * PPO_PROGRESS_TRAINING_CONTRACT.action_size
    mask[0] = mask[4] = True

    result = shapley_policy_margin_attribution(
        initial,
        candidate,
        (0.0,) * PPO_PROGRESS_TRAINING_CONTRACT.observation_size,
        tuple(mask),
    )

    assert result["margin_delta"] == pytest.approx(0.75)
    assert result["shapley_margin_delta"]["policy_head"] == pytest.approx(0.75)
    assert result["shapley_margin_delta"]["first_hidden"] == pytest.approx(0.0)
    assert result["shapley_margin_delta"]["second_hidden"] == pytest.approx(0.0)


def test_optimizer_attribution_rejects_output_overwrite_before_replay():
    output = Path(__file__)
    with pytest.raises(PPOContractError, match="output already exists"):
        run_progress_study_optimizer_attribution(
            output.parent / "missing-study",
            output,
            maximum_workers=1,
        )
