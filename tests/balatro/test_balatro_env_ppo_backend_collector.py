from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.action_encoding import action_index
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import (
    PRISTINE_LOSS_BACKEND_SCHEMA,
    PristineFirstBlindLossBackend,
    pristine_red_white_reset,
    sparse_terminal_reward,
)
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_REWARD_CONTRACT,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOPolicyOutput,
    PPOTrainingRun,
)
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.state import RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


class _InvalidTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(action=object())


def _environment(policy=None):
    return BalatroHeadlessEnvironment(
        PristineFirstBlindLossBackend(policy or _OneCardTacticalPolicy())
    )


def _ppo_output():
    probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
    probabilities[action_index(EnvAction.from_alias("SELECT_BLIND"))] = 1.0
    return PPOPolicyOutput(
        schema_version=PPO_POLICY_OUTPUT_SCHEMA,
        observation_version=PPO_TRAINING_CONTRACT.observation_version,
        action_version=PPO_TRAINING_CONTRACT.action_version,
        probabilities=tuple(probabilities),
        value_estimate=0.0,
    )


def test_env_ppo_backend_reset_is_exact_pristine_red_white_boundary():
    run = pristine_red_white_reset("BACKEND1")

    assert run.public.deck_name == "RED"
    assert run.public.stake_name == "WHITE"
    assert run.public.phase == "BLIND_SELECT"
    assert (run.public.ante, run.public.round, run.public.money) == (1, 0, 4)
    assert run.public.owned_deck == run.public.deck
    assert run.public.owned_deck is not run.public.deck
    assert run.blind_progression_state.small_status == "Select"
    assert run.blind_progression_state.blind_on_deck == "Small"
    assert run.public.blind.requirement == 300
    assert run.public.blind.reward == 3
    assert run.public.vouchers_observed is True
    assert run.public.vouchers == []
    assert run.public.shop_discount_percent_observed is True
    assert run.public.shop_discount_percent == 0


def test_env_ppo_backend_composes_select_and_tactical_owners_to_exact_loss():
    backend = PristineFirstBlindLossBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed="BACKEND2")

    assert environment.frame.status is RunStatus.RUNNING
    assert environment.frame.owner is TurnOwner.AGENT
    assert environment.legal_actions() == (EnvAction.from_alias("SELECT_BLIND"),)

    _, reward, terminated, truncated, info = environment.step(
        EnvAction.from_alias("SELECT_BLIND")
    )

    assert (reward, terminated, truncated) == (-1.0, True, False)
    assert environment.frame.status is RunStatus.LOSS
    assert environment.frame.owner is TurnOwner.TERMINAL
    assert environment.frame.state.phase == "GAME_OVER"
    assert environment.frame.state.hands_remaining == 0
    assert environment.frame.state.score < environment.frame.state.blind.requirement
    assert backend.run.blind_progression_state.small_status == "Current"
    assert info == {
        "backend_schema": PRISTINE_LOSS_BACKEND_SCHEMA,
        "reward_contract": PPO_REWARD_CONTRACT,
        "game_seed": "BACKEND2",
        "tactical_actions": 4,
    }
    assert environment.legal_actions() == ()


def test_env_ppo_backend_replay_and_snapshot_restore_are_deterministic():
    first = _environment()
    second = _environment()
    for environment in (first, second):
        environment.reset(seed="REPLAY")
        environment.step(EnvAction.from_alias("SELECT_BLIND"))

    assert first.serialize() == second.serialize()
    restored = _environment()
    observation, info = restored.restore(first.serialize())
    assert observation.phase == "GAME_OVER"
    assert restored.frame.status is RunStatus.LOSS
    assert info["tactical_actions"] == 4


def test_env_ppo_backend_invalid_tactical_or_snapshot_state_fails_closed():
    invalid = _environment(_InvalidTacticalPolicy())
    invalid.reset(seed="INVALID")
    before = invalid.serialize()

    with pytest.raises(HeadlessTransitionError, match="did not return BalatroAction"):
        invalid.step(EnvAction.from_alias("SELECT_BLIND"))
    assert invalid.serialize() == before

    with pytest.raises(HeadlessTransitionError, match="schema mismatch"):
        invalid.restore({**before, "schema": "old"})


def test_env_ppo_backend_clear_cashout_fails_closed_before_incomplete_shop():
    backend = PristineFirstBlindLossBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed="CLEAR")
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    before = backend.serialize()

    with pytest.raises(
        HeadlessTransitionError,
        match="complete normal shop inventory authority.*exact ordinary cash-out",
    ):
        environment.step(EnvAction.from_alias("SELECT_BLIND"))

    assert backend.serialize() == before
    assert environment.frame.status is RunStatus.RUNNING
    assert environment.frame.state.phase == "BLIND_SELECT"


def test_env_ppo_sparse_terminal_reward_contract_is_exact():
    assert sparse_terminal_reward(RunStatus.RUNNING) == 0.0
    assert sparse_terminal_reward(RunStatus.LOSS) == -1.0
    assert sparse_terminal_reward(RunStatus.ANTE_8_WIN) == 1.0
    with pytest.raises(TypeError):
        sparse_terminal_reward("LOSS")


def test_env_ppo_collector_records_complete_deterministic_terminal_episode():
    training_run = PPOTrainingRun.from_seed("COLLECT")
    calls = []

    def policy(observation, mask):
        calls.append((observation, mask))
        return _ppo_output()

    episode = collect_complete_ppo_episode(
        _environment(),
        training_run,
        episode_index=0,
        policy=policy,
    )

    assert len(calls) == 1
    assert episode.game_seed == training_run.game_seed(0)
    assert episode.action_count == 1
    assert episode.rewards == (-1.0,)
    assert episode.status is RunStatus.LOSS
    assert episode.boundaries[0].phase == "BLIND_SELECT"
    assert episode.boundaries[-1].phase == "GAME_OVER"
    assert episode.boundaries[-1].observation is None
    assert episode.decisions[0].action == EnvAction.from_alias("SELECT_BLIND")


def test_env_ppo_collector_rejects_noncontract_policy_output():
    with pytest.raises(PPOContractError, match="must return PPOPolicyOutput"):
        collect_complete_ppo_episode(
            _environment(),
            PPOTrainingRun.from_seed("BAD-POLICY"),
            episode_index=0,
            policy=lambda observation, mask: (1.0,) * len(mask.values),
        )
