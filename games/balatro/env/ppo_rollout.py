"""Complete-episode PPO rollout collection through the public environment API."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from games.balatro.env.action_encoding import ActionMask, legal_action_mask
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.observation_encoding import EncodedPublicObservation
from games.balatro.env.ppo_contract import (
    PPOContractError,
    PPOPolicyOutput,
    PPORolloutEpisode,
    PPOTrainingRun,
    ppo_training_contract_for_run,
    select_ppo_action,
)


PPOPolicy = Callable[[EncodedPublicObservation, ActionMask], PPOPolicyOutput]


def collect_complete_ppo_episode(
    environment: BalatroHeadlessEnvironment,
    training_run: PPOTrainingRun,
    *,
    episode_index: int,
    policy: PPOPolicy,
) -> PPORolloutEpisode:
    """Collect one reset-to-terminal episode without a fallback or truncation."""
    if not isinstance(environment, BalatroHeadlessEnvironment):
        raise TypeError("environment must be BalatroHeadlessEnvironment")
    if not isinstance(training_run, PPOTrainingRun):
        raise TypeError("training_run must be PPOTrainingRun")
    if not callable(policy):
        raise TypeError("policy must be callable")

    contract = ppo_training_contract_for_run(training_run)
    game_seed = training_run.game_seed(episode_index)
    _, reset_info = environment.reset(seed=game_seed)
    if reset_info.get("reward_contract") != contract.reward_contract:
        raise PPOContractError("PPO rollout reset reward contract mismatch")
    frames = [deepcopy(environment.frame)]
    decisions = []
    rewards = []

    for decision_index in range(contract.maximum_episode_actions):
        frame = environment.frame
        if frame.status.terminal:
            break
        observation = frame.encoded_observation()
        legal_actions = environment.legal_actions()
        mask = legal_action_mask(legal_actions)
        output = policy(observation, mask)
        if not isinstance(output, PPOPolicyOutput):
            raise PPOContractError("PPO policy must return PPOPolicyOutput")
        decision = select_ppo_action(
            training_run,
            episode_index=episode_index,
            decision_index=decision_index,
            observation=observation,
            legal_actions=legal_actions,
            policy_output=output,
        )
        _, reward, terminated, truncated, info = environment.step(decision.action)
        if info.get("reward_contract") != contract.reward_contract:
            raise PPOContractError("PPO rollout step reward contract mismatch")
        decisions.append(decision)
        rewards.append(reward)
        frames.append(deepcopy(environment.frame))
        if truncated:
            raise PPOContractError("truncated PPO rollouts are incomplete")
        if terminated:
            break
    else:
        raise PPOContractError("PPO rollout exceeded the frozen episode action cap")

    if not environment.frame.status.terminal:
        raise PPOContractError("PPO rollout did not reach a terminal boundary")
    return PPORolloutEpisode.completed(
        training_run,
        episode_index=episode_index,
        frames=frames,
        decisions=decisions,
        rewards=rewards,
    )
