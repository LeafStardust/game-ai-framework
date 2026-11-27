from dataclasses import FrozenInstanceError, replace
import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.action_encoding import action_index, legal_action_mask
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.joker_sale import can_sell_joker_exact
from games.balatro.env.observation_encoding import (
    JOKER_CENTER_KEYS,
    PUBLIC_OBSERVATION_SCHEMA,
    VOUCHER_KEYS,
)
from games.balatro.env.ppo_campaign import (
    make_ppo_tactical_decision_engine,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_contract import (
    PPO_ACTION_SAMPLE_DOMAIN,
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
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.mail_in_rebate import MailInRebateJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.jokers.to_the_moon import ToTheMoonJoker
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


def _fixed_action_policy(actions):
    actions = iter(actions)

    def replay(_observation, mask):
        action = next(actions)
        selected = action_index(action)
        assert mask.values[selected], action
        return replace(_policy_output(), probabilities=tuple(
            float(index == selected) for index in range(PPO_TRAINING_CONTRACT.action_size)
        ))

    return replay


def _generated_joker_lifecycle_policy(observation, mask):
    del observation
    priorities = (*range(11, 17), 2, 1, 3, 0, 26, 25)
    selected = next(index for index in priorities if mask.values[index])
    probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
    probabilities[selected] = 1.0
    return PPOPolicyOutput(
        schema_version=PPO_POLICY_OUTPUT_SCHEMA,
        observation_version=PPO_TRAINING_CONTRACT.observation_version,
        action_version=PPO_TRAINING_CONTRACT.action_version,
        probabilities=tuple(probabilities),
        value_estimate=0.0,
    )


def _voucher_lifecycle_policy(observation, mask):
    del observation
    priorities = (4, 0, 26)
    selected = next(index for index in priorities if mask.values[index])
    probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
    probabilities[selected] = 1.0
    return PPOPolicyOutput(
        schema_version=PPO_POLICY_OUTPUT_SCHEMA,
        observation_version=PPO_TRAINING_CONTRACT.observation_version,
        action_version=PPO_TRAINING_CONTRACT.action_version,
        probabilities=tuple(probabilities),
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
    assert (contract.observation_size, contract.action_size) == (3321, 27)
    assert contract.reward_contract == "balatro-red-white-sparse-terminal-reward-v1"
    assert contract.training_seed_policy == "derived_non_holdout_game_seeds"
    assert contract.rollout_episode_schema == PPO_ROLLOUT_EPISODE_SCHEMA
    assert contract.action_sample_domain == PPO_ACTION_SAMPLE_DOMAIN
    assert contract.policy_hidden_sizes == (512, 256)
    assert contract.rollout_batch_size == 2048
    assert contract.total_environment_steps == 2_097_152
    assert contract.to_json() == contract.to_json()
    assert json.loads(contract.to_json())["rollout_batch_size"] == 2048
    assert len(contract.sha256) == 64
    with pytest.raises(FrozenInstanceError):
        contract.learning_rate = 1.0


def _replace_observation_feature(observation, name, value):
    values = list(observation.values)
    values[PUBLIC_OBSERVATION_SCHEMA.feature_names.index(name)] = value
    return replace(observation, values=tuple(values))


def _observation_feature(observation, name):
    return observation.values[PUBLIC_OBSERVATION_SCHEMA.feature_names.index(name)]


@pytest.fixture(scope="module")
def episode_39_with_overstock():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(7),
        run,
        episode_index=39,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_overstock_boss_cashout(
    episode_39_with_overstock,
):
    episode = episode_39_with_overstock

    assert episode.game_seed == "B19790C4"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_VOUCHER",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before = episode.boundaries[6]
    after = episode.boundaries[7]
    assert (before.ante, before.phase, before.money) == (1, "BLIND_SELECT", 2)
    assert (after.ante, after.phase, after.money) == (2, "SHOP", 8)
    assert _observation_feature(
        before.observation,
        "vouchers.owned.v_overstock_norm",
    ) == 1.0
    assert _observation_feature(
        after.observation,
        "vouchers.owned.v_overstock_norm",
    ) == 1.0


@pytest.fixture(scope="module")
def episode_41_with_tarot_merchant():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(1),
        run,
        episode_index=41,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_acquires_exact_tarot_merchant(
    episode_41_with_tarot_merchant,
):
    episode = episode_41_with_tarot_merchant

    assert episode.game_seed == "20C74BCD"
    assert episode.action_count == 12
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_VOUCHER",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before = episode.boundaries[4]
    after = episode.boundaries[5]
    assert (before.ante, before.phase, before.money) == (1, "SHOP", 13)
    assert (after.ante, after.phase, after.money) == (1, "SHOP", 3)
    assert _observation_feature(
        before.observation,
        "vouchers.owned.v_tarot_merchant",
    ) == 0.0
    assert _observation_feature(
        after.observation,
        "vouchers.owned.v_tarot_merchant",
    ) == 1.0
    assert _observation_feature(
        before.observation, "state.tarot_rate"
    ) == 4.0
    assert _observation_feature(
        after.observation, "state.tarot_rate"
    ) == 9.6
    wrathful_center = float(JOKER_CENTER_KEYS.index("j_wrathful_joker") + 1)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.0.center"
    ) == wrathful_center


@pytest.fixture(scope="module")
def episode_45_with_generated_joker_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(5),
        run,
        episode_index=45,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_generated_droll_and_odd_todd_lifecycles(
    episode_45_with_generated_joker_lifecycles,
):
    episode = episode_45_with_generated_joker_lifecycles

    assert episode.game_seed == "F41B6F3A"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "BUY_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
        "SELL_JOKER",
        "BUY_JOKER",
        "SELL_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 5)

    before_sale = episode.boundaries[4]
    after_sale = episode.boundaries[5]
    assert (before_sale.ante, before_sale.phase, before_sale.money) == (
        1,
        "SHOP",
        13,
    )
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 15)

    before_odd_todd = episode.boundaries[5]
    after_odd_todd = episode.boundaries[6]
    assert (before_odd_todd.ante, before_odd_todd.phase, before_odd_todd.money) == (
        1,
        "SHOP",
        15,
    )
    assert (after_odd_todd.ante, after_odd_todd.phase, after_odd_todd.money) == (
        1,
        "SHOP",
        11,
    )
    assert episode.boundaries[7].money == 13


@pytest.fixture(scope="module")
def episode_12_with_walkie_talkie_and_even_steven_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(4),
        run,
        episode_index=12,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_walkie_crazy_and_even_lifecycles(
    episode_12_with_walkie_talkie_and_even_steven_lifecycles,
):
    episode = episode_12_with_walkie_talkie_and_even_steven_lifecycles

    assert episode.game_seed == "BAA636D2"
    assert episode.action_count == 15
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]

    walkie_center = float(JOKER_CENTER_KEYS.index("j_walkie_talkie") + 1)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.0.center"
    ) == walkie_center
    assert (episode.boundaries[2].ante, episode.boundaries[2].money) == (1, 5)
    assert _observation_feature(
        episode.boundaries[2].observation, "jokers.0.center"
    ) == walkie_center
    assert (episode.boundaries[3].ante, episode.boundaries[3].money) == (1, 7)
    assert _observation_feature(
        episode.boundaries[3].observation, "jokers.0.center"
    ) == 0.0

    crazy_center = float(JOKER_CENTER_KEYS.index("j_crazy") + 1)
    assert episode.decisions[5].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[5].observation, "shop.jokers.0.center"
    ) == crazy_center
    assert (episode.boundaries[6].money, episode.boundaries[7].money) == (9, 11)
    assert _observation_feature(
        episode.boundaries[6].observation, "jokers.0.center"
    ) == crazy_center
    assert _observation_feature(
        episode.boundaries[7].observation, "jokers.0.center"
    ) == 0.0

    before_buy = episode.boundaries[11]
    after_buy = episode.boundaries[12]
    after_sale = episode.boundaries[13]
    even_center = float(JOKER_CENTER_KEYS.index("j_even_steven") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (2, "SHOP", 25)
    assert episode.decisions[11].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.0.center",
    ) == even_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (2, "SHOP", 21)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == even_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (2, "SHOP", 23)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0


@pytest.fixture(scope="module")
def episode_21_with_banner_and_devious_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(5),
        run,
        episode_index=21,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_banner_and_devious_lifecycles(
    episode_21_with_banner_and_devious_lifecycles,
):
    episode = episode_21_with_banner_and_devious_lifecycles

    assert episode.game_seed == "1D88A8A1"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    banner_center = float(JOKER_CENTER_KEYS.index("j_banner") + 1)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.1.center"
    ) == banner_center
    assert _observation_feature(
        episode.boundaries[2].observation, "jokers.0.center"
    ) == banner_center
    assert _observation_feature(
        episode.boundaries[3].observation, "jokers.0.center"
    ) == 0.0
    before_buy = episode.boundaries[3]
    after_buy = episode.boundaries[4]
    after_sale = episode.boundaries[5]
    devious_center = float(JOKER_CENTER_KEYS.index("j_devious") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 4)
    assert episode.decisions[3].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.0.center",
    ) == devious_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 0)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == devious_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 2)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0


@pytest.fixture(scope="module")
def episode_31_with_gluttonous_abstract_and_mad_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(7),
        run,
        episode_index=31,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_gluttonous_abstract_and_mad_lifecycles(
    episode_31_with_gluttonous_abstract_and_mad_lifecycles,
):
    episode = episode_31_with_gluttonous_abstract_and_mad_lifecycles

    assert episode.game_seed == "19F511BC"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]

    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    gluttonous_center = float(JOKER_CENTER_KEYS.index("j_gluttenous_joker") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 7)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.1.center",
    ) == gluttonous_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 2)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == gluttonous_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 4)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0
    abstract_center = float(JOKER_CENTER_KEYS.index("j_abstract") + 1)
    assert (episode.boundaries[5].ante, episode.boundaries[5].money) == (1, 8)
    assert episode.decisions[5].action_mask.values[2] is True
    assert _observation_feature(
        episode.boundaries[5].observation,
        "shop.jokers.1.center",
    ) == abstract_center
    assert (episode.boundaries[6].ante, episode.boundaries[6].money) == (1, 4)
    assert _observation_feature(
        episode.boundaries[6].observation,
        "jokers.0.center",
    ) == abstract_center
    assert (episode.boundaries[7].ante, episode.boundaries[7].money) == (1, 6)
    assert _observation_feature(
        episode.boundaries[7].observation,
        "jokers.0.center",
    ) == 0.0
    mad_center = float(JOKER_CENTER_KEYS.index("j_mad") + 1)
    assert (episode.boundaries[9].ante, episode.boundaries[9].money) == (2, 12)
    assert episode.decisions[9].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[9].observation,
        "shop.jokers.0.center",
    ) == mad_center
    assert (episode.boundaries[10].ante, episode.boundaries[10].money) == (2, 8)
    assert _observation_feature(
        episode.boundaries[10].observation,
        "jokers.0.center",
    ) == mad_center
    assert (episode.boundaries[11].ante, episode.boundaries[11].money) == (2, 10)
    assert _observation_feature(
        episode.boundaries[11].observation,
        "jokers.0.center",
    ) == 0.0


@pytest.fixture(scope="module")
def episode_115_with_scholar_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=115,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_scholar_lifecycle(
    episode_115_with_scholar_lifecycle,
):
    episode = episode_115_with_scholar_lifecycle

    assert episode.game_seed == "58918DC7"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]

    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    scholar_center = float(JOKER_CENTER_KEYS.index("j_scholar") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.1.center",
    ) == scholar_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 5)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == scholar_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 7)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0


@pytest.fixture(scope="module")
def episode_34_with_blue_joker_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=34,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_blue_joker_lifecycle(
    episode_34_with_blue_joker_lifecycle,
):
    episode = episode_34_with_blue_joker_lifecycle

    assert episode.game_seed == "2B8499E6"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]

    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    blue_center = float(JOKER_CENTER_KEYS.index("j_blue_joker") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.0.center",
    ) == blue_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 3)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == blue_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 5)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0


@pytest.fixture(scope="module")
def episode_33_with_jolly_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=33,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_jolly_lifecycle(
    episode_33_with_jolly_lifecycle,
):
    episode = episode_33_with_jolly_lifecycle

    assert episode.game_seed == "A801C474"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]

    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    jolly_center = float(JOKER_CENTER_KEYS.index("j_jolly") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.0.center",
    ) == jolly_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 6)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == jolly_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 7)
    assert _observation_feature(
        after_sale.observation,
        "jokers.0.center",
    ) == 0.0
    wily_center = float(JOKER_CENTER_KEYS.index("j_wily") + 1)
    assert _observation_feature(
        episode.boundaries[5].observation,
        "shop.jokers.0.center",
    ) == wily_center
    assert _observation_feature(
        episode.boundaries[6].observation,
        "jokers.0.center",
    ) == wily_center
    assert (episode.boundaries[5].money, episode.boundaries[7].money) == (12, 10)


@pytest.fixture(scope="module")
def episode_35_with_sly_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=35,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_sly_lifecycle(
    episode_35_with_sly_lifecycle,
):
    episode = episode_35_with_sly_lifecycle
    assert episode.game_seed == "8E5CE4B5"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    sly_center = float(JOKER_CENTER_KEYS.index("j_sly") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.1.center"
    ) == sly_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 5)
    assert _observation_feature(after_buy.observation, "jokers.0.center") == sly_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 6)
    assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
    bull_center = float(JOKER_CENTER_KEYS.index("j_bull") + 1)
    before_bull = episode.boundaries[5]
    after_bull = episode.boundaries[6]
    after_bull_sale = episode.boundaries[7]
    assert _observation_feature(
        before_bull.observation, "shop.jokers.0.center"
    ) == bull_center
    assert (before_bull.money, after_bull.money, after_bull_sale.money) == (11, 5, 8)
    assert _observation_feature(after_bull.observation, "jokers.0.center") == bull_center
    assert _observation_feature(after_bull_sale.observation, "jokers.0.center") == 0.0


@pytest.fixture(scope="module")
def episode_10_with_wily_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=10,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_wily_lifecycle(
    episode_10_with_wily_lifecycle,
):
    episode = episode_10_with_wily_lifecycle
    assert episode.game_seed == "435A60DF"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    wily_center = float(JOKER_CENTER_KEYS.index("j_wily") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == wily_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 5)
    assert _observation_feature(after_buy.observation, "jokers.0.center") == wily_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 7)
    assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0


@pytest.fixture(scope="module")
def episode_27_with_abstract_and_scary_face_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=27,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_abstract_and_scary_face_lifecycles(
    episode_27_with_abstract_and_scary_face_lifecycles,
):
    episode = episode_27_with_abstract_and_scary_face_lifecycles
    assert episode.game_seed == "68E835DA"
    assert episode.action_count == 11
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    abstract_center = float(JOKER_CENTER_KEYS.index("j_abstract") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.1.center"
    ) == abstract_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 4)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == abstract_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 6)
    assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
    scary_face_center = float(JOKER_CENTER_KEYS.index("j_scary_face") + 1)
    assert episode.decisions[3].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[3].observation, "shop.jokers.0.center"
    ) == scary_face_center
    assert (episode.boundaries[4].ante, episode.boundaries[4].money) == (1, 2)
    assert _observation_feature(
        episode.boundaries[4].observation, "jokers.0.center"
    ) == scary_face_center
    assert (episode.boundaries[5].ante, episode.boundaries[5].money) == (1, 4)
    assert _observation_feature(
        episode.boundaries[5].observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_46_with_smiley_face_and_blue_joker_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=46,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_smiley_greedy_and_blue_lifecycles(
    episode_46_with_smiley_face_and_blue_joker_lifecycles,
):
    episode = episode_46_with_smiley_face_and_blue_joker_lifecycles
    assert episode.game_seed == "9AC8FAC6"
    assert episode.action_count == 11
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    smiley_center = float(JOKER_CENTER_KEYS.index("j_smiley") + 1)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.1.center"
    ) == smiley_center
    assert (episode.boundaries[2].money, episode.boundaries[3].money) == (5, 7)
    assert _observation_feature(
        episode.boundaries[2].observation, "jokers.0.center"
    ) == smiley_center
    assert _observation_feature(
        episode.boundaries[3].observation, "jokers.0.center"
    ) == 0.0
    blue_center = float(JOKER_CENTER_KEYS.index("j_blue_joker") + 1)
    greedy_center = float(JOKER_CENTER_KEYS.index("j_greedy_joker") + 1)
    assert _observation_feature(
        episode.boundaries[5].observation, "shop.jokers.1.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[6].observation, "jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[7].observation, "jokers.0.center"
    ) == 0.0
    assert _observation_feature(
        episode.boundaries[7].observation, "shop.jokers.0.center"
    ) == blue_center


@pytest.fixture(scope="module")
def episode_62_with_raised_fist_lifecycle():
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=62,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_raised_fist_lifecycle(
    episode_62_with_raised_fist_lifecycle,
):
    episode = episode_62_with_raised_fist_lifecycle
    assert episode.game_seed == "43F62C55"
    assert episode.action_count == 17
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions[:4]
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
    ]
    raised_fist_center = float(JOKER_CENTER_KEYS.index("j_raised_fist") + 1)
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.1.center"
    ) == raised_fist_center
    assert (episode.boundaries[1].money, episode.boundaries[2].money) == (10, 5)
    assert _observation_feature(
        episode.boundaries[2].observation, "jokers.0.center"
    ) == raised_fist_center
    assert episode.boundaries[3].money == 7
    assert _observation_feature(
        episode.boundaries[3].observation, "jokers.0.center"
    ) == 0.0
    bull_center = float(JOKER_CENTER_KEYS.index("j_bull") + 1)
    assert episode.decisions[11].action == EnvAction.from_alias(
        "BUY_JOKER", {"slot": 0}
    )
    assert episode.decisions[12].action == EnvAction.from_alias(
        "SELL_JOKER", {"joker_index": 0}
    )
    assert _observation_feature(
        episode.boundaries[11].observation, "shop.jokers.0.center"
    ) == bull_center
    assert (
        episode.boundaries[11].money,
        episode.boundaries[12].money,
        episode.boundaries[13].money,
    ) == (18, 12, 15)
    assert _observation_feature(
        episode.boundaries[12].observation, "jokers.0.center"
    ) == bull_center
    assert _observation_feature(
        episode.boundaries[13].observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_5_with_clever_joker_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=5,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_clever_joker_lifecycle(
    episode_5_with_clever_joker_lifecycle,
):
    episode = episode_5_with_clever_joker_lifecycle
    assert episode.game_seed == "59B15C34"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    clever_center = float(JOKER_CENTER_KEYS.index("j_clever") + 1)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[1].observation, "shop.jokers.0.center"
    ) == clever_center
    assert (episode.boundaries[1].money, episode.boundaries[2].money) == (8, 4)
    assert _observation_feature(
        episode.boundaries[2].observation, "jokers.0.center"
    ) == clever_center
    assert episode.boundaries[3].money == 6
    assert _observation_feature(
        episode.boundaries[3].observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_140_with_mad_joker_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=140,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_mad_joker_lifecycle(
    episode_140_with_mad_joker_lifecycle,
):
    episode = episode_140_with_mad_joker_lifecycle
    assert episode.game_seed == "7FBB953D"
    assert episode.action_count == 15
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    mad_center = float(JOKER_CENTER_KEYS.index("j_mad") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[1] is False
    assert episode.decisions[1].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.1.center"
    ) == mad_center
    assert (after_buy.money, after_sale.money) == (4, 6)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == mad_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0
@pytest.fixture(scope="module")
def episode_24_with_zany_joker_lifecycle():
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=24,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_zany_joker_lifecycle(
    episode_24_with_zany_joker_lifecycle,
):
    episode = episode_24_with_zany_joker_lifecycle
    assert episode.game_seed == "66F36434"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    zany_center = float(JOKER_CENTER_KEYS.index("j_zany") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == zany_center
    assert (after_buy.money, after_sale.money) == (4, 6)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == zany_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_110_with_crafty_joker_lifecycle():
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=110,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_crafty_joker_lifecycle(
    episode_110_with_crafty_joker_lifecycle,
):
    episode = episode_110_with_crafty_joker_lifecycle
    assert episode.game_seed == "6C803767"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    crafty_center = float(JOKER_CENTER_KEYS.index("j_crafty") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert episode.decisions[1].action_mask.values[2] is False
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == crafty_center
    assert (after_buy.money, after_sale.money) == (5, 7)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == crafty_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_12_with_crazy_joker_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=12,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_crazy_joker_lifecycle(
    episode_12_with_crazy_joker_lifecycle,
):
    episode = episode_12_with_crazy_joker_lifecycle
    assert episode.game_seed == "BAA636D2"
    assert episode.action_count == 15
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    crazy_center = float(JOKER_CENTER_KEYS.index("j_crazy") + 1)
    before_buy = episode.boundaries[5]
    after_buy = episode.boundaries[6]
    after_sale = episode.boundaries[7]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 13)
    assert episode.decisions[5].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == crazy_center
    assert (after_buy.money, after_sale.money) == (9, 11)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == crazy_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_13_with_greedy_joker_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=13,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_greedy_joker_lifecycle(
    episode_13_with_greedy_joker_lifecycle,
):
    episode = episode_13_with_greedy_joker_lifecycle
    assert episode.game_seed == "D691C2E4"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    greedy_center = float(JOKER_CENTER_KEYS.index("j_greedy_joker") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert episode.decisions[1].action_mask.values[2] is False
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == greedy_center
    assert (after_buy.money, after_sale.money) == (4, 6)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_8_with_lusty_joker_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=8,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_lusty_joker_lifecycle(
    episode_8_with_lusty_joker_lifecycle,
):
    episode = episode_8_with_lusty_joker_lifecycle
    assert episode.game_seed == "E4205D09"
    assert episode.action_count == 11
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    lusty_center = float(JOKER_CENTER_KEYS.index("j_lusty_joker") + 1)
    before_buy = episode.boundaries[3]
    after_buy = episode.boundaries[4]
    after_sale = episode.boundaries[5]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 6)
    assert episode.decisions[3].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == lusty_center
    assert (after_buy.money, after_sale.money) == (1, 3)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == lusty_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_41_with_wrathful_joker_lifecycle():
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(1),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=41,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_wrathful_joker_lifecycle(
    episode_41_with_wrathful_joker_lifecycle,
):
    episode = episode_41_with_wrathful_joker_lifecycle
    assert episode.game_seed == "20C74BCD"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    wrathful_center = float(JOKER_CENTER_KEYS.index("j_wrathful_joker") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 10)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == wrathful_center
    assert (after_buy.money, after_sale.money) == (5, 7)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == wrathful_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_50_with_fibonacci_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(2),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=50,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_fibonacci_lifecycle(
    episode_50_with_fibonacci_lifecycle,
):
    episode = episode_50_with_fibonacci_lifecycle
    assert episode.game_seed == "05B3FF62"
    assert episode.action_count == 17
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    fibonacci_center = float(JOKER_CENTER_KEYS.index("j_fibonacci") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == fibonacci_center
    assert (after_buy.money, after_sale.money) == (1, 5)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == fibonacci_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0
    juggler_center = float(JOKER_CENTER_KEYS.index("j_juggler") + 1)
    before_juggler = episode.boundaries[11]
    after_juggler = episode.boundaries[12]
    after_juggler_sale = episode.boundaries[13]
    assert _observation_feature(
        before_juggler.observation, "shop.jokers.1.center"
    ) == juggler_center
    assert (
        _observation_feature(before_juggler.observation, "state.hand_size"),
        _observation_feature(after_juggler.observation, "state.hand_size"),
        _observation_feature(after_juggler_sale.observation, "state.hand_size"),
    ) == (8.0, 9.0, 8.0)
    assert (before_juggler.money, after_juggler.money, after_juggler_sale.money) == (
        16,
        12,
        14,
    )


@pytest.fixture(scope="module")
def episode_25_with_juggler_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(1),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=25,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_juggler_lifecycle(
    episode_25_with_juggler_lifecycle,
):
    episode = episode_25_with_juggler_lifecycle
    assert episode.game_seed == "2C383F87"
    assert episode.action_count == 11
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    juggler_center = float(JOKER_CENTER_KEYS.index("j_juggler") + 1)
    before_buy = episode.boundaries[3]
    after_buy = episode.boundaries[4]
    after_sale = episode.boundaries[5]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 13)
    assert episode.decisions[3].action_mask.values[2] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.1.center"
    ) == juggler_center
    assert (after_buy.money, after_sale.money) == (9, 11)
    assert (
        _observation_feature(before_buy.observation, "state.hand_size"),
        _observation_feature(after_buy.observation, "state.hand_size"),
        _observation_feature(after_sale.observation, "state.hand_size"),
    ) == (8.0, 9.0, 8.0)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == juggler_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_54_with_drunkard_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(6),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=54,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_drunkard_and_rocket_lifecycles(
    episode_54_with_drunkard_lifecycle,
):
    episode = episode_54_with_drunkard_lifecycle
    assert episode.game_seed == "D26BD190"
    assert episode.action_count == 17
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    drunkard_center = float(JOKER_CENTER_KEYS.index("j_drunkard") + 1)
    before_buy = episode.boundaries[3]
    after_buy = episode.boundaries[4]
    after_sale = episode.boundaries[5]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 12)
    assert episode.decisions[3].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == drunkard_center
    assert (after_buy.money, after_sale.money) == (8, 10)
    assert (
        _observation_feature(before_buy.observation, "state.round_reset_discards"),
        _observation_feature(after_buy.observation, "state.round_reset_discards"),
        _observation_feature(after_sale.observation, "state.round_reset_discards"),
    ) == (3.0, 4.0, 3.0)
    assert (
        _observation_feature(before_buy.observation, "state.discards_remaining"),
        _observation_feature(after_buy.observation, "state.discards_remaining"),
        _observation_feature(after_sale.observation, "state.discards_remaining"),
    ) == (3.0, 3.0, 3.0)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == drunkard_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0
    rocket_center = float(JOKER_CENTER_KEYS.index("j_rocket") + 1)
    before_rocket = episode.boundaries[13]
    after_rocket = episode.boundaries[14]
    after_rocket_sale = episode.boundaries[15]
    assert _observation_feature(
        before_rocket.observation, "shop.jokers.0.center"
    ) == rocket_center
    assert (before_rocket.money, after_rocket.money, after_rocket_sale.money) == (
        18,
        12,
        15,
    )
    assert _observation_feature(
        after_rocket.observation, "jokers.0.center"
    ) == rocket_center
    assert _observation_feature(
        after_rocket.observation, "jokers.0.dollars"
    ) == 1.0
    assert _observation_feature(
        after_rocket.observation, "jokers.0.increase"
    ) == 2.0
    assert _observation_feature(
        after_rocket_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_4_with_golden_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(4),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=4,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_golden_lifecycle(
    episode_4_with_golden_lifecycle,
):
    episode = episode_4_with_golden_lifecycle
    assert episode.game_seed == "A0370D8B"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    golden_center = float(JOKER_CENTER_KEYS.index("j_golden") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 7)
    assert episode.decisions[1].action_mask.values[1] is True
    assert episode.decisions[1].action_mask.values[2] is False
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == golden_center
    assert (after_buy.money, after_sale.money) == (1, 4)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == golden_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0
    bull_center = float(JOKER_CENTER_KEYS.index("j_bull") + 1)
    before_bull = episode.boundaries[5]
    after_bull = episode.boundaries[6]
    after_bull_sale = episode.boundaries[7]
    assert episode.decisions[5].action_mask.values[2] is True
    assert _observation_feature(
        before_bull.observation, "shop.jokers.1.center"
    ) == bull_center
    assert (before_bull.money, after_bull.money, after_bull_sale.money) == (9, 3, 6)
    assert _observation_feature(after_bull.observation, "jokers.0.center") == bull_center
    assert _observation_feature(after_bull_sale.observation, "jokers.0.center") == 0.0


@pytest.fixture(scope="module")
def episode_78_with_bull_lifecycle():
    return collect_complete_ppo_episode(
        make_ppo_training_environment(6),
        PPOTrainingRun.from_seed("RED-WHITE-PPO-V1"),
        episode_index=78,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_bull_lifecycle(
    episode_78_with_bull_lifecycle,
):
    episode = episode_78_with_bull_lifecycle
    assert episode.game_seed == "2F061DB4"
    assert episode.action_count == 5
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    bull_center = float(JOKER_CENTER_KEYS.index("j_bull") + 1)
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == bull_center
    assert (after_buy.money, after_sale.money) == (3, 6)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == bull_center
    assert _observation_feature(
        after_sale.observation, "jokers.0.center"
    ) == 0.0


def test_env_ppo_fixed_seed_completes_exact_generated_rocket_lifecycle():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="57815055")
    actions = []
    money = [environment.frame.state.money]

    for _ in range(100):
        if environment.frame.status.terminal:
            break
        legal = environment.legal_actions()
        run = environment._backend.run
        rocket_slot = next(
            (
                index
                for index, item in enumerate(run.public.shop_jokers)
                if getattr(item, "center_key", None) == "j_rocket"
            ),
            None,
        )
        candidates = []
        if run.public.jokers:
            candidates.append(
                EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
            )
        if rocket_slot is not None:
            candidates.append(
                EnvAction.from_alias("BUY_JOKER", {"slot": rocket_slot})
            )
        candidates.extend(
            (
                EnvAction.from_alias("END_SHOP"),
                EnvAction.from_alias("SELECT_BLIND"),
            )
        )
        action = next(candidate for candidate in candidates if candidate in legal)
        environment.step(action)
        actions.append((action.alias, action.payload()))
        money.append(environment.frame.state.money)

    assert environment.frame.status is RunStatus.LOSS
    assert environment.frame.state.ante == 1
    assert actions == [
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    assert money == [4, 9, 9, 15, 9, 12, 12, 12]


def test_env_ppo_trace_seed_buys_diet_cola_and_carries_its_double_tag():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="062DA0EA")
    for alias, payload, money, tags in (
        ("SELECT_BLIND", {}, 8, 0),
        ("END_SHOP", {}, 8, 0),
        ("SELECT_BLIND", {}, 14, 0),
        ("BUY_JOKER", {"slot": 0}, 8, 0),
        ("SELL_JOKER", {"joker_index": 0}, 11, 1),
        ("END_SHOP", {}, 11, 1),
        ("SELECT_BLIND", {}, 19, 1),
        ("END_SHOP", {}, 19, 1),
    ):
        action = EnvAction.from_alias(alias, payload)
        assert action in environment.legal_actions()
        before = environment._backend.run
        rng = before.rng_snapshot()
        if alias == "SELL_JOKER":
            assert before.public.jokers[0].center == "j_diet_cola"
            debuffed = before.copy()
            debuffed.public.jokers[0].debuffed = True
            assert not can_sell_joker_exact(debuffed, 0)
        environment.step(action)
        after = environment._backend.run
        assert after.public.money == money
        assert after.tags == ["tag_double"] * tags
        assert environment.frame.encoded_observation().values[-1] == float(tags)
        if alias == "SELL_JOKER":
            assert after.public.jokers == []
            assert after.rng_snapshot() == rng
            assert "tag_double" in after.tag_profile_state.discovered_center_keys
            assert before.tags == []

    assert environment.frame.state.ante == 2


def test_env_ppo_trace_seed_completes_moon_purchase_interest_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="062DA0EA")
    replay = (
        ("SELECT_BLIND", {}, 8, False),
        ("BUY_JOKER", {"slot": 0}, 3, True),
        ("END_SHOP", {}, 3, True),
        ("SELECT_BLIND", {}, 8, True),
        ("END_SHOP", {}, 8, True),
        ("SELECT_BLIND", {}, 16, True),
        ("SELL_JOKER", {"joker_index": 0}, 18, False),
        ("END_SHOP", {}, 18, False),
        ("SELECT_BLIND", {}, 25, False),
    )
    for alias, params, money, owns_moon in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [ToTheMoonJoker] * owns_moon
        if owns_moon:
            assert run.generated_center_discovered("j_to_the_moon") is True

    assert environment.frame.state.round == 4
    assert environment.frame.state.phase == "SHOP"


def test_env_ppo_trace_seed_completes_mail_purchase_payout_and_sale():
    class MatchingDiscard:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.money_before = None
            self.payout = None

        def decide(self, state):
            if state.round == 2 and self.money_before is None:
                cards = [
                    card for card in state.hand
                    if not card.face_down and not card.debuffed
                    and card.rank == state.jokers[0].rank
                ]
                if cards and state.discards_remaining:
                    self.money_before = state.money
                    return SimpleNamespace(action=BalatroAction(DISCARD_CARDS, cards=cards))
            elif self.money_before is not None and self.payout is None:
                self.payout = state.money - self.money_before
            return self.tactical.decide(state)

    policy = MatchingDiscard()
    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(policy))
    environment.reset(seed="FADDC372")
    replay = (
        ("SELECT_BLIND", {}, 9, "7", False),
        ("BUY_JOKER", {"slot": 0}, 5, "7", True),
        ("END_SHOP", {}, 5, "7", True),
        ("SELECT_BLIND", {}, 17, "9", True),
        ("SELL_JOKER", {"joker_index": 0}, 19, "9", False),
        ("END_SHOP", {}, 19, "9", False),
        ("SELECT_BLIND", {}, 19, "9", False),
    )
    for alias, params, money, rank, owns_mail in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert run.mail_rebate_rank == rank
        assert [type(joker) for joker in run.public.jokers] == [MailInRebateJoker] * owns_mail
        if owns_mail:
            assert run.public.jokers[0].rank == rank
            assert run.generated_center_discovered("j_mail") is True

    assert policy.payout == 5
    assert environment.frame.state.round == 3
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_trace_seed_completes_sixth_sense_purchase_destruction_and_sale():
    class FirstBigBlindSix:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.played = False

        def decide(self, state):
            if state.round == 2 and not self.played:
                six = next((card for card in state.hand if card.rank == "6"), None)
                if six is not None:
                    self.played = True
                    return SimpleNamespace(action=BalatroAction(PLAY_CARDS, cards=[six]))
                if state.discards_remaining:
                    return SimpleNamespace(
                        action=BalatroAction(DISCARD_CARDS, cards=state.hand[:5])
                    )
            return self.tactical.decide(state)

    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(FirstBigBlindSix()))
    environment.reset(seed="4C8AAC2C")
    replay = (
        ("SELECT_BLIND", {}, 8, False, False),
        ("BUY_JOKER", {"slot": 0}, 2, True, False),
        ("END_SHOP", {}, 2, True, False),
        ("SELECT_BLIND", {}, 7, True, True),
        ("SELL_JOKER", {"joker_index": 0}, 10, False, True),
        ("END_SHOP", {}, 10, False, True),
        ("SELECT_BLIND", {}, 18, False, True),
    )
    for alias, params, money, owns_sixth, destroyed in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [SixthSenseJoker] * owns_sixth
        assert len(run.public.owned_deck) == 52 - int(destroyed)
        assert run.removed_base_six_suits == ("Hearts",) * destroyed
        assert [card.center_key for card in run.public.consumables] == ["c_ouija"] * destroyed
        assert ("Spectralsixth1" in run.rng.nodes) is destroyed
        if owns_sixth:
            assert run.generated_center_discovered("j_sixth_sense") is True
        assert all(candidate.alias != "USE_CONSUMABLE" for candidate in environment.legal_actions())

    assert environment.frame.state.round == 3
    assert environment.frame.state.phase == "SHOP"


@pytest.mark.parametrize("missing", ["order", "spectral"])
def test_env_ppo_sixth_sense_buy_requires_exact_authority(missing):
    environment = make_ppo_training_environment(0)
    environment.reset(seed="4C8AAC2C")
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert buy in environment.legal_actions()
    run = environment._backend.run
    if missing == "order":
        run.playing_card_order = None
    else:
        del run.generation_discovery["c_ouija"]

    assert buy not in environment.legal_actions()
    with pytest.raises(ValueError, match="illegal action"):
        environment.step(buy)


def test_env_ppo_trace_seed_completes_green_purchase_growth_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="243A32A8")
    replay = (
        ("SELECT_BLIND", {}, 8, ()),
        ("BUY_JOKER", {"slot": 0}, 4, (0,)),
        ("END_SHOP", {}, 4, (0,)),
        ("SELECT_BLIND", {}, 10, (2,)),
        ("END_SHOP", {}, 10, (2,)),
        ("SELECT_BLIND", {}, 19, (4,)),
        ("SELL_JOKER", {"joker_index": 0}, 21, ()),
        ("END_SHOP", {}, 21, ()),
        ("SELECT_BLIND", {}, 28, ()),
    )
    for alias, params, money, mult in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert all(type(joker) is GreenJoker for joker in run.public.jokers)
        assert tuple(joker.mult for joker in run.public.jokers) == mult
        if mult:
            assert run.generated_center_discovered("j_green_joker") is True
            assert _observation_feature(
                environment.frame.encoded_observation(), "jokers.0.mult"
            ) == float(mult[0])

    assert environment.frame.state.round == 4
    assert environment.frame.state.phase == "SHOP"


def test_env_ppo_trace_seed_completes_supernova_purchase_scoring_and_sale():
    class RecordingPolicy:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.first_boss_score = None

        def decide(self, state):
            if state.round == 3 and state.score and self.first_boss_score is None:
                hand = state.last_played_hand
                self.first_boss_score = (hand, state.hand_play_counts[hand], state.score)
            return self.tactical.decide(state)

    policy = RecordingPolicy()
    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(policy))
    environment.reset(seed="EB851E5F")
    replay = (
        ("SELECT_BLIND", {}, 7, False),
        ("END_SHOP", {}, 7, False),
        ("SELECT_BLIND", {}, 12, False),
        ("BUY_JOKER", {"slot": 1}, 7, True),
        ("END_SHOP", {}, 7, True),
        ("SELECT_BLIND", {}, 14, True),
        ("SELL_JOKER", {"joker_index": 0}, 16, False),
        ("END_SHOP", {}, 16, False),
        ("SELECT_BLIND", {}, 16, False),
    )
    for alias, params, money, owns_supernova in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [SupernovaJoker] * owns_supernova
        if owns_supernova:
            assert run.generated_center_discovered("j_supernova") is True

    assert policy.first_boss_score == ("TWO_PAIR", 6, 480)
    assert environment.frame.state.round == 4
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_seed_completes_runner_purchase_growth_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=164)
    replay = (
        ("SELECT_BLIND", {}, 9, ()),
        ("BUY_JOKER", {"slot": 1}, 4, (0,)),
        ("END_SHOP", {}, 4, (0,)),
        ("SELECT_BLIND", {}, 9, (15,)),
        ("END_SHOP", {}, 9, (15,)),
        ("SELECT_BLIND", {}, 16, (15,)),
        ("SELL_JOKER", {"joker_index": 0}, 18, ()),
        ("END_SHOP", {}, 18, ()),
        ("SELECT_BLIND", {}, 24, ()),
    )
    for alias, params, money, chips in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert all(type(joker) is RunnerJoker for joker in run.public.jokers)
        assert tuple(joker.chips for joker in run.public.jokers) == chips
        if chips:
            assert run.generated_center_discovered("j_runner") is True
            assert _observation_feature(
                environment.frame.encoded_observation(), "jokers.0.chips"
            ) == float(chips[0])

    assert environment.frame.state.round == 4
    assert environment.frame.state.phase == "SHOP"


def test_env_ppo_trace_seed_completes_splash_purchase_scoring_and_sale():
    class RecordingPolicy:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.first_scored_big_blind_hand = None

        def decide(self, state):
            if state.round == 2 and state.score and self.first_scored_big_blind_hand is None:
                self.first_scored_big_blind_hand = (state.last_played_hand, state.score)
            return self.tactical.decide(state)

    policy = RecordingPolicy()
    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(policy))
    environment.reset(seed="EB851E5F")
    replay = (
        ("SELECT_BLIND", {}, 7, False),
        ("BUY_JOKER", {"slot": 1}, 4, True),
        ("END_SHOP", {}, 4, True),
        ("SELECT_BLIND", {}, 10, True),
        ("SELL_JOKER", {"joker_index": 0}, 11, False),
        ("END_SHOP", {}, 11, False),
        ("SELECT_BLIND", {}, 19, False),
    )
    for alias, params, money, owns_splash in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [SplashJoker] * owns_splash
        if owns_splash:
            assert run.generated_center_discovered("j_splash") is True

    # The three 3s score alongside two ten-chip face-card kickers.
    assert policy.first_scored_big_blind_hand == ("THREE_OF_A_KIND", 177)
    assert environment.frame.state.round == 3
    assert environment.frame.state.phase == "SHOP"


def test_env_ppo_trace_seed_completes_faceless_purchase_payout_and_sale():
    class FirstQualifyingDiscard:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.before_payout = None
            self.payout = None

        def decide(self, state):
            if self.before_payout is not None and self.payout is None:
                self.payout = state.money - self.before_payout
            if self.before_payout is None and state.jokers and state.discards_remaining:
                faces = [
                    card for card in state.hand
                    if not card.face_down and not card.debuffed
                    and card.rank in {"J", "Q", "K"}
                ]
                if len(faces) >= 3:
                    self.before_payout = state.money
                    return SimpleNamespace(
                        action=BalatroAction(DISCARD_CARDS, cards=faces[:3])
                    )
            return self.tactical.decide(state)

    policy = FirstQualifyingDiscard()
    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(policy))
    environment.reset(seed="FF526426")
    replay = (
        ("SELECT_BLIND", {}, 8, False),
        ("BUY_JOKER", {"slot": 1}, 4, True),
        ("END_SHOP", {}, 4, True),
        ("SELECT_BLIND", {}, 8, True),
        ("END_SHOP", {}, 8, True),
        ("SELECT_BLIND", {}, 21, True),
        ("SELL_JOKER", {"joker_index": 0}, 23, False),
        ("END_SHOP", {}, 23, False),
        ("SELECT_BLIND", {}, 30, False),
    )
    for alias, params, money, owns_faceless in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [FacelessJoker] * owns_faceless
        if owns_faceless:
            assert run.generated_center_discovered("j_faceless") is True

    assert policy.payout == 5
    assert environment.frame.state.round == 4
    assert environment.frame.state.phase == "SHOP"


def test_env_ppo_roadmap_seed_completes_dna_purchase_copy_and_sale():
    class FirstBigBlindSingleCard:
        def __init__(self):
            self.tactical = make_ppo_tactical_decision_engine()
            self.played = False

        def decide(self, state):
            if state.round == 2 and not self.played:
                self.played = True
                return SimpleNamespace(
                    action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
                )
            return self.tactical.decide(state)

    environment = BalatroHeadlessEnvironment(PPOHeadlessBackend(FirstBigBlindSingleCard()))
    environment.reset(seed="64FD54A0")
    replay = (
        ("SELECT_BLIND", {}, 8, False, 52),
        ("BUY_JOKER", {"slot": 0}, 0, True, 52),
        ("END_SHOP", {}, 0, True, 52),
        ("SELECT_BLIND", {}, 4, True, 53),
        ("SELL_JOKER", {"joker_index": 0}, 8, False, 53),
        ("END_SHOP", {}, 8, False, 53),
        ("SELECT_BLIND", {}, 8, False, 53),
    )
    for alias, params, money, owns_dna, count in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [type(joker) for joker in run.public.jokers] == [DNAJoker] * owns_dna
        assert len(run.public.owned_deck) == count
        order = run.require_playing_card_order()
        assert len(order) == count
        if owns_dna:
            assert run.generated_center_discovered("j_dna") is True
        if count == 53:
            copy = order[52]
            assert (copy.rank, copy.suit) == ("Q", "Spades")
            assert any(card is copy for card in run.public.owned_deck)
        if environment.frame.status is RunStatus.RUNNING:
            assert _observation_feature(
                environment.frame.encoded_observation(), "owned_deck.52.present"
            ) == float(count == 53)

    assert environment.frame.state.round == 3
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_roadmap_seed_completes_midas_purchase_conversion_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="0B58B2B9")
    replay = (
        ("SELECT_BLIND", {}, 10, False, ()),
        ("BUY_JOKER", {"slot": 0}, 3, True, ()),
        ("END_SHOP", {}, 3, True, ()),
        ("SELECT_BLIND", {}, 9, True, (("Q", "Diamonds"),)),
        ("SELL_JOKER", {"joker_index": 0}, 12, False, (("Q", "Diamonds"),)),
        ("END_SHOP", {}, 12, False, (("Q", "Diamonds"),)),
        ("SELECT_BLIND", {}, 12, False, (("Q", "Diamonds"),)),
    )
    for alias, params, money, owns_midas, expected_gold in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [joker.center for joker in run.public.jokers] == ["j_midas_mask"] * owns_midas
        assert tuple(
            (card.rank, card.suit) for card in run.public.owned_deck
            if card.enhancement == "Gold"
        ) == expected_gold
        if owns_midas:
            assert run.generated_center_discovered("j_midas_mask") is True

    assert environment.frame.state.round == 3
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_roadmap_seed_completes_madness_purchase_growth_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="382C0AB9")
    replay = (
        ("SELECT_BLIND", {}, 8, ()),
        ("BUY_JOKER", {"slot": 0}, 1, (1.0,)),
        ("END_SHOP", {}, 1, (1.0,)),
        ("SELECT_BLIND", {}, 6, (1.5,)),
        ("END_SHOP", {}, 6, (1.5,)),
        ("SELECT_BLIND", {}, 12, (1.5,)),
        ("SELL_JOKER", {"joker_index": 0}, 15, ()),
        ("END_SHOP", {}, 15, ()),
        ("SELECT_BLIND", {}, 15, ()),
    )
    for alias, params, money, multipliers in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert tuple(joker.x_mult for joker in run.public.jokers) == multipliers
        assert all(joker.center == "j_madness" for joker in run.public.jokers)
        assert "madness" not in run.rng.nodes

    assert environment.frame.state.ante == 2
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_fixed_seed_completes_mime_purchase_boss_win_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=107)
    replay = (
        ("SELECT_BLIND", {}, 7, 0),
        ("BUY_JOKER", {"slot": 1}, 2, 1),
        ("END_SHOP", {}, 2, 1),
        ("SELECT_BLIND", {}, 7, 1),
        ("END_SHOP", {}, 7, 1),
        ("SELECT_BLIND", {}, 13, 1),
        ("SELL_JOKER", {"joker_index": 0}, 15, 0),
        ("END_SHOP", {}, 15, 0),
        ("SELECT_BLIND", {}, 15, 0),
    )
    for alias, params, money, owned_count in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [joker.center for joker in run.public.jokers] == ["j_mime"] * owned_count
        if alias == "BUY_JOKER":
            assert run.generated_center_discovered("j_mime") is True

    assert environment.frame.state.ante == 2
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_fixed_seed_completes_seance_purchase_round_win_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=145)
    replay = (
        ("SELECT_BLIND", {}, 10, 0),
        ("BUY_JOKER", {"slot": 0}, 4, 1),
        ("END_SHOP", {}, 4, 1),
        ("SELECT_BLIND", {}, 9, 1),
        ("SELL_JOKER", {"joker_index": 0}, 12, 0),
        ("END_SHOP", {}, 12, 0),
        ("SELECT_BLIND", {}, 12, 0),
    )
    for alias, params, money, owned_count in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [joker.center for joker in run.public.jokers] == ["j_seance"] * owned_count
        if alias == "BUY_JOKER":
            assert run.generated_center_discovered("j_seance") is True

    assert environment.frame.state.round == 3
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_fixed_seed_completes_cloud9_purchase_payouts_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=48)
    replay = (
        ("SELECT_BLIND", {}, 7, 0),
        ("BUY_JOKER", {"slot": 1}, 0, 1),
        ("END_SHOP", {}, 0, 1),
        ("SELECT_BLIND", {}, 10, 1),
        ("END_SHOP", {}, 10, 1),
        ("SELECT_BLIND", {}, 22, 1),
        ("SELL_JOKER", {"joker_index": 0}, 25, 0),
        ("END_SHOP", {}, 25, 0),
        ("SELECT_BLIND", {}, 33, 0),
        ("END_SHOP", {}, 33, 0),
        ("SELECT_BLIND", {}, 33, 0),
    )
    for alias, params, money, owned_count in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert run.public.money == money
        assert [joker.center for joker in run.public.jokers] == ["j_cloud_9"] * owned_count
        if alias == "BUY_JOKER":
            assert run.generated_center_discovered("j_cloud_9") is True

    assert environment.frame.state.ante == 2
    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_fixed_seed_completes_castle_purchase_round_win_and_sale():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=51)
    replay = (
        ("SELECT_BLIND", {}, 9, "Spades", ()),
        ("BUY_JOKER", {"slot": 0}, 3, "Spades", (("j_castle", "Spades", 0),)),
        ("END_SHOP", {}, 3, "Spades", (("j_castle", "Spades", 0),)),
        ("SELECT_BLIND", {}, 7, "Clubs", (("j_castle", "Clubs", 6),)),
        ("SELL_JOKER", {"joker_index": 0}, 10, "Clubs", ()),
        ("END_SHOP", {}, 10, "Clubs", ()),
        ("SELECT_BLIND", {}, 10, "Clubs", ()),
    )
    for alias, params, money, suit, jokers in replay:
        action = EnvAction.from_alias(alias, params)
        assert action in environment.legal_actions()
        environment.step(action)
        run = environment._backend.run
        assert (run.public.money, run.castle_suit) == (money, suit)
        assert tuple((joker.center, joker.suit, joker.chips) for joker in run.public.jokers) == jokers

    assert environment.frame.status is RunStatus.LOSS


def test_env_ppo_fixed_seed_completes_exact_generated_vampire_lifecycle():
    environment = make_ppo_training_environment(0)
    environment.reset(seed=69)
    actions = []
    money = [environment.frame.state.money]

    for _ in range(100):
        if environment.frame.status.terminal:
            break
        legal = environment.legal_actions()
        run = environment._backend.run
        vampire_slot = next(
            (
                index
                for index, item in enumerate(run.public.shop_jokers)
                if getattr(item, "center_key", None) == "j_vampire"
            ),
            None,
        )
        candidates = []
        if run.public.jokers:
            candidates.append(
                EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
            )
        if vampire_slot is not None:
            candidates.append(
                EnvAction.from_alias("BUY_JOKER", {"slot": vampire_slot})
            )
        candidates.extend(
            (
                EnvAction.from_alias("END_SHOP"),
                EnvAction.from_alias("SELECT_BLIND"),
            )
        )
        action = next(candidate for candidate in candidates if candidate in legal)
        environment.step(action)
        actions.append((action.alias, action.payload()))
        money.append(environment.frame.state.money)

    assert environment.frame.status is RunStatus.LOSS
    assert environment.frame.state.ante == 2
    assert actions == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    assert money == [4, 8, 1, 4, 4, 8, 8, 15, 15, 21, 21, 21]


@pytest.fixture(scope="module")
def episode_9_with_photograph_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=9,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_generated_photograph_lifecycle(
    episode_9_with_photograph_lifecycle,
):
    episode = episode_9_with_photograph_lifecycle
    assert episode.game_seed == "4104A2D5"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    photograph_center = float(JOKER_CENTER_KEYS.index("j_photograph") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 8)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == photograph_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 3)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == photograph_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 5)
    assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
    clever_center = float(JOKER_CENTER_KEYS.index("j_clever") + 1)
    clever_before_buy = episode.boundaries[9]
    clever_after_buy = episode.boundaries[10]
    clever_after_sale = episode.boundaries[11]
    assert (clever_before_buy.ante, clever_before_buy.phase) == (2, "SHOP")
    assert episode.decisions[9].action_mask.values[2] is True
    assert _observation_feature(
        clever_before_buy.observation, "shop.jokers.1.center"
    ) == clever_center
    assert (
        clever_before_buy.money,
        clever_after_buy.money,
        clever_after_sale.money,
    ) == (25, 21, 23)
    assert _observation_feature(
        clever_after_buy.observation, "jokers.0.center"
    ) == clever_center
    assert _observation_feature(
        clever_after_sale.observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_65_with_half_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=65,
        policy=_generated_joker_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_two_exact_generated_half_lifecycles(
    episode_65_with_half_lifecycles,
):
    episode = episode_65_with_half_lifecycles
    assert episode.game_seed == "08718DA1"
    assert episode.action_count == 9
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    half_center = float(JOKER_CENTER_KEYS.index("j_half") + 1)
    for decision_index, before_index, after_index, sale_index in (
        (1, 1, 2, 3),
        (5, 5, 6, 7),
    ):
        before_buy = episode.boundaries[before_index]
        after_buy = episode.boundaries[after_index]
        after_sale = episode.boundaries[sale_index]
        assert episode.decisions[decision_index].action_mask.values[1] is True
        assert _observation_feature(
            before_buy.observation, "shop.jokers.0.center"
        ) == half_center
        assert _observation_feature(
            after_buy.observation, "jokers.0.center"
        ) == half_center
        assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
    assert [episode.boundaries[index].money for index in (1, 2, 3, 5, 6, 7)] == [
        7,
        2,
        4,
        9,
        4,
        6,
    ]


@pytest.fixture(scope="module")
def episode_59_with_mystic_summit_lifecycles():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 1}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=59,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_two_exact_generated_mystic_summit_lifecycles(
    episode_59_with_mystic_summit_lifecycles,
):
    episode = episode_59_with_mystic_summit_lifecycles
    assert episode.game_seed == "3293F37E"
    assert episode.action_count == 15
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 1}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    mystic_center = float(JOKER_CENTER_KEYS.index("j_mystic_summit") + 1)
    for decision_index, before_index, after_index, sale_index, shop_slot in (
        (1, 1, 2, 3, 1),
        (5, 5, 6, 7, 0),
    ):
        before_buy = episode.boundaries[before_index]
        after_buy = episode.boundaries[after_index]
        after_sale = episode.boundaries[sale_index]
        assert episode.decisions[decision_index].action_mask.values[
            shop_slot + 1
        ] is True
        assert _observation_feature(
            before_buy.observation, f"shop.jokers.{shop_slot}.center"
        ) == mystic_center
        assert _observation_feature(
            after_buy.observation, "jokers.0.center"
        ) == mystic_center
        assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
    assert [episode.boundaries[index].money for index in (1, 2, 3, 5, 6, 7)] == [
        7,
        2,
        4,
        10,
        5,
        7,
    ]
    greedy_center = float(JOKER_CENTER_KEYS.index("j_greedy_joker") + 1)
    assert _observation_feature(
        episode.boundaries[9].observation, "shop.jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[10].observation, "jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[11].observation, "jokers.0.center"
    ) == 0.0


@pytest.fixture(scope="module")
def episode_6_with_banner_lifecycle():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(0),
        run,
        episode_index=6,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_generated_banner_lifecycle(
    episode_6_with_banner_lifecycle,
):
    episode = episode_6_with_banner_lifecycle
    assert episode.game_seed == "FE98D556"
    assert episode.action_count == 7
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [
        (decision.action.alias, decision.action.payload())
        for decision in episode.decisions
    ] == [
        ("SELECT_BLIND", {}),
        ("BUY_JOKER", {"slot": 0}),
        ("SELL_JOKER", {"joker_index": 0}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
        ("END_SHOP", {}),
        ("SELECT_BLIND", {}),
    ]
    before_buy = episode.boundaries[1]
    after_buy = episode.boundaries[2]
    after_sale = episode.boundaries[3]
    banner_center = float(JOKER_CENTER_KEYS.index("j_banner") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 9)
    assert episode.decisions[1].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation, "shop.jokers.0.center"
    ) == banner_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 4)
    assert _observation_feature(
        after_buy.observation, "jokers.0.center"
    ) == banner_center
    assert (after_sale.ante, after_sale.phase, after_sale.money) == (1, "SHOP", 6)
    assert _observation_feature(after_sale.observation, "jokers.0.center") == 0.0
@pytest.fixture(scope="module")
def episode_46_with_paint_brush():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(6),
        run,
        episode_index=46,
        policy=_voucher_lifecycle_policy,
    )


def test_env_ppo_rollout_crosses_exact_paint_brush_boss_tactics(
    episode_46_with_paint_brush,
):
    episode = episode_46_with_paint_brush

    assert episode.game_seed == "9AC8FAC6"
    assert episode.action_count == 10
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_VOUCHER",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before = episode.boundaries[5]
    after = episode.boundaries[6]
    assert (before.ante, before.phase, before.money) == (1, "BLIND_SELECT", 4)
    assert (after.ante, after.phase, after.money) == (2, "SHOP", 11)
    assert _observation_feature(before.observation, "state.hand_size") == 9.0
    assert _observation_feature(
        before.observation,
        "vouchers.owned.v_paint_brush",
    ) == 1.0
    assert _observation_feature(after.observation, "state.hand_size") == 9.0
    assert _observation_feature(
        after.observation,
        "vouchers.owned.v_paint_brush",
    ) == 1.0


@pytest.fixture(scope="module")
def episode_313_with_wheel_redraws():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(1),
        run,
        episode_index=313,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_devious_purchase_and_wheel_redraws(
    episode_313_with_wheel_redraws,
):
    episode = episode_313_with_wheel_redraws

    assert episode.game_seed == "88DB75F5"
    assert episode.action_count == 6
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert episode.boundaries[-1].ante == 1
    assert episode.boundaries[-1].score == 576
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before_buy = episode.boundaries[3]
    after_buy = episode.boundaries[4]
    devious_center = float(JOKER_CENTER_KEYS.index("j_devious") + 1)
    assert (before_buy.ante, before_buy.phase, before_buy.money) == (1, "SHOP", 14)
    assert episode.decisions[3].action.payload() == {"slot": 0}
    assert episode.decisions[3].action_mask.values[1] is True
    assert _observation_feature(
        before_buy.observation,
        "shop.jokers.0.center",
    ) == devious_center
    assert (after_buy.ante, after_buy.phase, after_buy.money) == (1, "SHOP", 10)
    assert _observation_feature(
        after_buy.observation,
        "jokers.0.center",
    ) == devious_center


@pytest.fixture(scope="module")
def episode_413_with_house_play_facing():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(5),
        run,
        episode_index=413,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_house_play_facing(
    episode_413_with_house_play_facing,
):
    episode = episode_413_with_house_play_facing

    assert episode.game_seed == "DDE9AB93"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert episode.boundaries[-1].ante == 1
    assert episode.boundaries[-1].score == 132
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "BUY_VOUCHER",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]


@pytest.fixture(scope="module")
def episode_50_with_hieroglyph():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(2),
        run,
        episode_index=50,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_hieroglyph_boss_cashout(
    episode_50_with_hieroglyph,
):
    episode = episode_50_with_hieroglyph

    assert episode.game_seed == "05B3FF62"
    assert episode.action_count == 24
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_JOKER",
        "BUY_VOUCHER",
        "SELL_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
        "REROLL_SHOP",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "BUY_JOKER",
        "SELL_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_JOKER",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before = episode.boundaries[7]
    after = episode.boundaries[8]
    assert (before.ante, before.phase, before.money) == (0, "BLIND_SELECT", 3)
    assert (after.ante, after.phase, after.money) == (1, "SHOP", 8)
    for boundary in (before, after):
        assert _observation_feature(
            boundary.observation,
            "vouchers.owned.v_hieroglyph",
        ) == 1.0
        assert _observation_feature(
            boundary.observation,
            "state.round_reset_hands",
        ) == 3.0
    greedy_center = float(JOKER_CENTER_KEYS.index("j_greedy_joker") + 1)
    assert episode.decisions[3].action_mask.values[2] is True
    assert _observation_feature(
        episode.boundaries[3].observation, "shop.jokers.1.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[4].observation, "jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[6].observation, "jokers.0.center"
    ) == 0.0
    banner_center = float(JOKER_CENTER_KEYS.index("j_banner") + 1)
    assert episode.decisions[14].action_mask.values[1] is True
    assert _observation_feature(
        episode.boundaries[14].observation, "shop.jokers.0.center"
    ) == banner_center
    assert _observation_feature(
        episode.boundaries[15].observation, "jokers.0.center"
    ) == banner_center
    assert _observation_feature(
        episode.boundaries[16].observation, "jokers.0.center"
    ) == 0.0
    sly_center = float(JOKER_CENTER_KEYS.index("j_sly") + 1)
    assert _observation_feature(
        episode.boundaries[18].observation, "shop.jokers.0.center"
    ) == sly_center
    assert _observation_feature(
        episode.boundaries[19].observation, "jokers.0.center"
    ) == sly_center
    assert _observation_feature(
        episode.boundaries[23].observation, "jokers.0.center"
    ) == sly_center
    assert episode.boundaries[-1].score == 708


@pytest.fixture(scope="module")
def episode_86_with_flint():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    return collect_complete_ppo_episode(
        make_ppo_training_environment(6),
        run,
        episode_index=86,
        policy=PPOActorCritic(run).infer,
    )


def test_env_ppo_rollout_crosses_exact_flint_play_boundary(
    episode_86_with_flint,
):
    episode = episode_86_with_flint

    assert episode.game_seed == "7D4CD200"
    assert episode.action_count == 12
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_JOKER",
        "SELL_JOKER",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    before = episode.boundaries[11]
    after = episode.boundaries[12]
    assert (before.ante, before.phase, before.money) == (2, "BLIND_SELECT", 23)
    assert (after.ante, after.phase, after.money) == (2, "GAME_OVER", 23)
    assert _observation_feature(before.observation, "state.hand_size") == 8.0
    greedy_center = float(JOKER_CENTER_KEYS.index("j_greedy_joker") + 1)
    assert _observation_feature(
        episode.boundaries[7].observation, "shop.jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[8].observation, "jokers.0.center"
    ) == greedy_center
    assert _observation_feature(
        episode.boundaries[9].observation, "jokers.0.center"
    ) == 0.0
    assert episode.boundaries[-1].score == 1044


@pytest.fixture(scope="module")
def episode_89_with_reroll():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    # Keep the mechanics replay on its intended actions as new offers become legal.
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )

    return collect_complete_ppo_episode(
        make_ppo_training_environment(1),
        run,
        episode_index=89,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_rerolls_and_blue_joker_lifecycle(
    episode_89_with_reroll,
):
    episode = episode_89_with_reroll

    assert episode.game_seed == "C749D4F7"
    assert episode.action_count == 13
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "REROLL_SHOP",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_CONSUMABLE",
        "END_SHOP",
        "SELECT_BLIND",
        "BUY_JOKER",
        "SELL_JOKER",
        "REROLL_SHOP",
        "REROLL_SHOP",
        "END_SHOP",
        "SELECT_BLIND",
    ]

    assert (episode.boundaries[1].phase, episode.boundaries[1].money) == (
        "SHOP",
        10,
    )
    assert (episode.boundaries[2].phase, episode.boundaries[2].money) == (
        "SHOP",
        5,
    )
    assert (episode.boundaries[7].ante, episode.boundaries[7].money) == (2, 15)
    assert (episode.boundaries[8].ante, episode.boundaries[8].money) == (2, 10)
    assert (episode.boundaries[9].ante, episode.boundaries[9].money) == (2, 12)
    assert (episode.boundaries[10].ante, episode.boundaries[10].money) == (2, 7)
    assert (episode.boundaries[11].ante, episode.boundaries[11].money) == (2, 1)
    blue_center = float(JOKER_CENTER_KEYS.index("j_blue_joker") + 1)
    assert _observation_feature(
        episode.boundaries[7].observation,
        "shop.jokers.0.center",
    ) == blue_center
    assert _observation_feature(
        episode.boundaries[8].observation,
        "jokers.0.center",
    ) == blue_center


@pytest.fixture(scope="module")
def episode_102_with_first_shop_reroll():
    run = PPOTrainingRun.from_seed("RED-WHITE-PPO-V1")
    actions = (
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
        EnvAction.from_alias("END_SHOP"),
        EnvAction.from_alias("SELECT_BLIND"),
    )
    return collect_complete_ppo_episode(
        make_ppo_training_environment(6),
        run,
        episode_index=102,
        policy=_fixed_action_policy(actions),
    )


def test_env_ppo_rollout_crosses_exact_first_shop_reroll_and_boss_cashout(
    episode_102_with_first_shop_reroll,
):
    episode = episode_102_with_first_shop_reroll

    assert episode.game_seed == "0058185F"
    assert episode.action_count == 8
    assert episode.rewards[-1] == -1.0
    assert episode.boundaries[-1].status is RunStatus.LOSS
    assert [decision.action.alias for decision in episode.decisions] == [
        "SELECT_BLIND",
        "REROLL_SHOP",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
        "END_SHOP",
        "SELECT_BLIND",
    ]
    after_reroll = episode.boundaries[2]
    assert (after_reroll.ante, after_reroll.phase, after_reroll.money) == (
        1,
        "SHOP",
        4,
    )
    after_boss_cashout = episode.boundaries[6]
    assert (after_boss_cashout.phase, after_boss_cashout.money) == ("SHOP", 19)


def test_env_ppo_rollout_admits_exact_observed_hieroglyph_ante_decrement(
    episode_50_with_hieroglyph,
):
    episode = episode_50_with_hieroglyph
    decreases = [
        (index, before.ante, after.ante, decision.action.alias)
        for index, (before, after, decision) in enumerate(
            zip(episode.boundaries[:-1], episode.boundaries[1:], episode.decisions)
        )
        if after.ante < before.ante
    ]

    assert episode.game_seed == "05B3FF62"
    assert episode.action_count == 24
    assert decreases == [(4, 1, 0, "BUY_VOUCHER")]

    after = episode.boundaries[5]
    zero_observation = _replace_observation_feature(
        after.observation, "state.ante", 0.0
    )
    assert replace(after, ante=0, observation=zero_observation).ante == 0
    with pytest.raises(PPOContractError, match="at least 0"):
        replace(after, ante=-1)


def test_env_ppo_rollout_admits_exact_observed_petroglyph_ante_decrement(
    episode_50_with_hieroglyph,
):
    episode = episode_50_with_hieroglyph
    boundaries = list(episode.boundaries)
    decisions = list(episode.decisions)
    before = boundaries[4]
    after = boundaries[5]
    before_observation = _replace_observation_feature(
        before.observation,
        "shop.vouchers.0.center",
        float(VOUCHER_KEYS.index("v_petroglyph") + 1),
    )
    before_observation = _replace_observation_feature(
        before_observation, "vouchers.owned.v_hieroglyph", 1.0
    )
    after_observation = _replace_observation_feature(
        after.observation, "vouchers.owned.v_petroglyph", 1.0
    )
    boundaries[4] = replace(before, observation=before_observation)
    boundaries[5] = replace(after, observation=after_observation)
    decisions[4] = replace(decisions[4], observation=before_observation)
    decisions[5] = replace(decisions[5], observation=after_observation)

    assert replace(
        episode, boundaries=tuple(boundaries), decisions=tuple(decisions)
    ).action_count == 24


@pytest.mark.parametrize(
    ("boundary_index", "feature", "value"),
    (
        (
            4,
            "shop.vouchers.0.center",
            float(VOUCHER_KEYS.index("v_overstock_norm") + 1),
        ),
        (
            4,
            "shop.vouchers.0.center",
            float(VOUCHER_KEYS.index("v_petroglyph") + 1),
        ),
        (5, "vouchers.owned.v_hieroglyph", 0.0),
        (5, "shop.vouchers.0.present", 1.0),
    ),
)
def test_env_ppo_rollout_rejects_unproven_ante_voucher_decrement(
    episode_50_with_hieroglyph, boundary_index, feature, value
):
    episode = episode_50_with_hieroglyph
    boundaries = list(episode.boundaries)
    decisions = list(episode.decisions)
    boundary = boundaries[boundary_index]
    observation = _replace_observation_feature(boundary.observation, feature, value)
    boundaries[boundary_index] = replace(boundary, observation=observation)
    if boundary_index < len(decisions):
        decisions[boundary_index] = replace(
            decisions[boundary_index], observation=observation
        )

    with pytest.raises(PPOContractError, match="progression decrease is not exact"):
        replace(
            episode,
            boundaries=tuple(boundaries),
            decisions=tuple(decisions),
        )


def test_env_ppo_rollout_rejects_non_voucher_ante_decrement_action(
    episode_50_with_hieroglyph,
):
    episode = episode_50_with_hieroglyph
    decisions = list(episode.decisions)
    decisions[4] = select_ppo_action(
        episode.training_run,
        episode_index=50,
        decision_index=4,
        observation=episode.boundaries[4].observation,
        legal_actions=(EnvAction.from_alias("END_SHOP"),),
        policy_output=_policy_output(),
    )

    with pytest.raises(PPOContractError, match="progression decrease is not exact"):
        replace(episode, decisions=tuple(decisions))


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
    assert episode.boundaries[-1].observation is None
    assert episode.to_json() == episode.to_json()
    payload = json.loads(episode.to_json())
    assert payload["training_run"]["contract_sha256"] == PPO_TRAINING_CONTRACT.sha256
    assert payload["decisions"][0]["action"]["alias"] == "SELECT_BLIND"
    assert payload["decisions"][0]["value_estimate"] == 0.0
    assert payload["boundaries"][-1]["observation"] is None
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

def test_env_ppo_trace_seed_buys_and_sells_exact_egg():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="062DA0EA")
    for alias in ("SELECT_BLIND", "END_SHOP") * 3 + ("SELECT_BLIND",):
        environment.step(EnvAction.from_alias(alias))

    assert environment.frame.state.money == 30
    environment.step(EnvAction.from_alias("BUY_JOKER", {"slot": 0}))
    egg = environment.frame.state.jokers[0]
    assert (egg.center, egg.sell_value, egg.sell_cost) == ("j_egg", 0, 2)
    environment.step(EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}))
    assert environment.frame.state.money == 28
    assert environment.frame.state.jokers == []


def test_env_ppo_trace_seed_buys_and_sells_exact_shortcut():
    environment = make_ppo_training_environment(0)
    environment.reset(seed="062DA0EA")
    for alias in ("SELECT_BLIND", "END_SHOP") * 3 + ("SELECT_BLIND",):
        environment.step(EnvAction.from_alias(alias))

    state = environment.frame.state
    assert state.money == 30
    offer = state.shop_jokers[1]
    assert (offer.center_key, offer.price, offer.edition) == ("j_shortcut", 7, None)
    rng = environment._backend.run.rng_snapshot()

    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    assert buy in environment.legal_actions()
    environment.step(buy)
    state = environment.frame.state
    assert state.money == 23
    assert [(joker.center, joker.sell_cost) for joker in state.jokers] == [
        ("j_shortcut", 3)
    ]

    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert environment.frame.state.money == 26
    assert environment.frame.state.jokers == []
    assert environment._backend.run.rng_snapshot() == rng
