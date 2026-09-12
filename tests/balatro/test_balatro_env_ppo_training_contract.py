from dataclasses import FrozenInstanceError, replace
import json

import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.action_encoding import legal_action_mask
from games.balatro.env.actions import EnvAction
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_ROLLOUT_EPISODE_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPO_TRAINING_CONTRACT_VERSION,
    PPOContractError,
    PPOPolicyOutput,
    PPORolloutEpisode,
    PPOTrainingRun,
    select_ppo_action,
)
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.state import BalatroState


def _frame(*, terminal=False, money=4):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.money = money
    state.score = 0
    state.blind = create_small_blind(300)
    return EnvStateFrame(
        state,
        status=RunStatus.LOSS if terminal else RunStatus.RUNNING,
        owner=TurnOwner.TERMINAL if terminal else TurnOwner.AGENT,
    )


def _policy_output(value=1.0):
    return PPOPolicyOutput(
        schema_version=PPO_POLICY_OUTPUT_SCHEMA,
        observation_version=PPO_TRAINING_CONTRACT.observation_version,
        action_version=PPO_TRAINING_CONTRACT.action_version,
        probabilities=(value,) * PPO_TRAINING_CONTRACT.action_size,
        value_estimate=0.0,
    )


def _decision(run, frame=None):
    frame = _frame() if frame is None else frame
    return select_ppo_action(
        run,
        episode_index=0,
        decision_index=0,
        observation=frame.encoded_observation(),
        legal_actions=(EnvAction.from_alias("SELECT_BLIND"),),
        policy_output=_policy_output(),
    )


def test_env_ppo_training_design_is_frozen_and_binds_every_input_contract():
    contract = PPO_TRAINING_CONTRACT

    assert contract.version == PPO_TRAINING_CONTRACT_VERSION
    assert contract.algorithm == "clipped_ppo"
    assert (contract.observation_size, contract.action_size) == (2444, 27)
    assert contract.reward_contract == "canonical_backend_reward_only"
    assert contract.training_seed_policy == "derived_non_holdout_game_seeds"
    assert contract.policy_hidden_sizes == (512, 256)
    assert contract.rollout_batch_size == 2048
    assert contract.total_environment_steps == 2_097_152
    assert contract.to_json() == contract.to_json()
    assert json.loads(contract.to_json())["rollout_batch_size"] == 2048
    assert len(contract.sha256) == 64
    with pytest.raises(FrozenInstanceError):
        contract.learning_rate = 1.0


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "unknown"},
        {"observation_size": 1},
        {"action_size": 1},
        {"reward_contract": "shaped"},
        {"policy_hidden_sizes": (64,)},
        {"parallel_environments": 1},
        {"learning_rate": 0.001},
        {"total_environment_steps": 1},
    ],
)
def test_env_ppo_training_contract_drift_requires_a_new_version(changes):
    with pytest.raises(PPOContractError, match="has drifted"):
        replace(PPO_TRAINING_CONTRACT, **changes)


def test_env_ppo_training_run_derives_separate_reproducible_non_holdout_streams():
    first = PPOTrainingRun.from_seed("red-white-training-1")
    second = PPOTrainingRun.from_seed("red-white-training-1")

    assert first == second
    assert first.learner_seed_hex != first.rollout_seed_hex
    assert first.game_seed(0) == second.game_seed(0)
    assert first.game_seed(0) != first.game_seed(1)
    assert first.game_seed(0) not in {spec.game_seed for spec in FIXED_SEEDED_EPISODES}
    assert first.to_json() == second.to_json()
    with pytest.raises(PPOContractError, match="learner seed provenance"):
        replace(first, learner_seed_hex="0" * 64)


def test_env_ppo_decision_masks_illegal_mass_and_samples_reproducibly():
    run = PPOTrainingRun.from_seed(7)
    frame = _frame()
    first = _decision(run, frame)
    second = _decision(run, frame)

    assert first == second
    assert first.action == EnvAction.from_alias("SELECT_BLIND")
    assert first.probabilities[first.action_index] == 1.0
    assert all(
        probability == 0.0
        for index, probability in enumerate(first.probabilities)
        if index != first.action_index
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_env_ppo_nonfinite_or_negative_policy_outputs_fail_closed(value):
    with pytest.raises(PPOContractError, match="finite|nonnegative"):
        _policy_output(value)


def test_env_ppo_nonfinite_value_estimate_fails_closed():
    with pytest.raises(PPOContractError, match="value estimate must be finite"):
        replace(_policy_output(), value_estimate=float("nan"))


def test_env_ppo_schema_empty_mask_and_illegal_sample_fail_closed():
    run = PPOTrainingRun.from_seed(7)
    frame = _frame()
    with pytest.raises(PPOContractError, match="schema version"):
        replace(_policy_output(), schema_version="old")
    with pytest.raises(PPOContractError, match="empty legal action mask"):
        select_ppo_action(
            run,
            episode_index=0,
            decision_index=0,
            observation=frame.encoded_observation(),
            legal_actions=(),
            policy_output=_policy_output(),
        )

    decision = _decision(run, frame)
    end_shop_mask = legal_action_mask((EnvAction.from_alias("END_SHOP"),))
    with pytest.raises(PPOContractError, match="illegal action"):
        replace(
            decision,
            action_mask=end_shop_mask,
            probabilities=tuple(1.0 if allowed else 0.0 for allowed in end_shop_mask.values),
        )


def test_env_ppo_completed_rollout_preserves_terminal_episode_provenance():
    run = PPOTrainingRun.from_seed("complete")
    first = _frame(money=4)
    final = _frame(terminal=True, money=2)
    decision = _decision(run, first)

    episode = PPORolloutEpisode.completed(
        run,
        episode_index=0,
        frames=(first, final),
        decisions=(decision,),
        rewards=(-1.0,),
    )

    assert episode.schema_version == PPO_ROLLOUT_EPISODE_SCHEMA
    assert episode.game_seed == run.game_seed(0)
    assert episode.action_count == 1
    assert episode.status is RunStatus.LOSS
    assert episode.boundaries[0].money == 4
    assert episode.to_json() == episode.to_json()
    payload = json.loads(episode.to_json())
    assert payload["training_run"]["contract_sha256"] == PPO_TRAINING_CONTRACT.sha256
    assert payload["decisions"][0]["action"]["alias"] == "SELECT_BLIND"
    assert payload["decisions"][0]["value_estimate"] == 0.0
    first.state.money = 999
    assert episode.boundaries[0].money == 4


def test_env_ppo_incomplete_truncated_and_tampered_rollouts_fail_closed():
    run = PPOTrainingRun.from_seed("incomplete")
    first = _frame()
    final = _frame(terminal=True)
    decision = _decision(run, first)

    with pytest.raises(PPOContractError, match="terminal boundary"):
        PPORolloutEpisode.completed(
            run,
            episode_index=0,
            frames=(first, _frame()),
            decisions=(decision,),
            rewards=(0.0,),
        )
    with pytest.raises(PPOContractError, match="incomplete"):
        PPORolloutEpisode.completed(
            run,
            episode_index=0,
            frames=(first, final),
            decisions=(decision,),
            rewards=(0.0,),
            truncated=True,
        )
    with pytest.raises(PPOContractError, match="provenance drifted"):
        PPORolloutEpisode.completed(
            run,
            episode_index=1,
            frames=(first, final),
            decisions=(decision,),
            rewards=(0.0,),
        )
    with pytest.raises(PPOContractError, match="finite"):
        PPORolloutEpisode.completed(
            run,
            episode_index=0,
            frames=(first, final),
            decisions=(decision,),
            rewards=(float("nan"),),
        )


def test_env_ppo_terminal_diagnostic_authority_fails_closed_on_contradiction():
    run = PPOTrainingRun.from_seed("terminal-authority")
    first = _frame()
    decision = _decision(run, first)
    cleared_loss = _frame(terminal=True)
    cleared_loss.state.score = 300
    missing_requirement = _frame(terminal=True)
    missing_requirement.state.blind = None

    with pytest.raises(PPOContractError, match="already satisfies"):
        PPORolloutEpisode.completed(
            run,
            episode_index=0,
            frames=(first, cleared_loss),
            decisions=(decision,),
            rewards=(0.0,),
        )
    with pytest.raises(PPOContractError, match="no blind requirement"):
        PPORolloutEpisode.completed(
            run,
            episode_index=0,
            frames=(first, missing_requirement),
            decisions=(decision,),
            rewards=(0.0,),
        )
