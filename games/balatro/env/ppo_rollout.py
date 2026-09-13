"""Complete-episode PPO rollout collection through the public environment API."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from games.balatro.env.action_encoding import ActionMask, legal_action_mask
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.observation_encoding import EncodedPublicObservation
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOPolicyOutput,
    PPORolloutEpisode,
    PPOTrainingRun,
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

    game_seed = training_run.game_seed(episode_index)
    environment.reset(seed=game_seed)
    frames = [deepcopy(environment.frame)]
    decisions = []
    rewards = []

    for decision_index in range(PPO_TRAINING_CONTRACT.maximum_episode_actions):
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
        _, reward, terminated, truncated, _ = environment.step(decision.action)
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
