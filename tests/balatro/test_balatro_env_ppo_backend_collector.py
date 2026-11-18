from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import BlindType
from games.balatro.env.action_encoding import action_index
from games.balatro.env.action_encoding import legal_action_mask
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import (
    PPO_HEADLESS_BACKEND_SCHEMA,
    PPOHeadlessBackend,
    pristine_red_white_reset,
    sparse_terminal_reward,
)
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_PROGRESS_REWARD_CONTRACT,
    PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPO_REWARD_CONTRACT,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOPolicyOutput,
    PPORolloutBoundary,
    PPOTrainingRun,
)
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.state import RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.hand import PokerHand
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.scoring import BalatroScorer


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


class _InvalidTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(action=object())


class _FiveCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=list(state.hand[:5]))
        )


class _RecordingOneCardTacticalPolicy:
    def __init__(self):
        self.hands = []

    def decide(self, state):
        self.hands.append(
            tuple((card.face_down, card.rank, card.suit) for card in state.hand)
        )
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


def _environment(policy=None):
    return BalatroHeadlessEnvironment(
        PPOHeadlessBackend(policy or _OneCardTacticalPolicy())
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
    assert all(
        card.played_this_ante_observed
        for card in run.require_playing_card_order()
    )
    assert not any(
        card.played_this_ante
        for card in run.require_playing_card_order()
    )
    assert run.public.joker_generation_pool_observed is True
    assert run.public.consumable_generation_pool_observed is True
    assert run.public.voucher_generation_pool_observed is True
    assert run.generated_center_discovered("j_joker") is True


def test_env_ppo_backend_composes_select_and_tactical_owners_to_exact_loss():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
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
        "backend_schema": PPO_HEADLESS_BACKEND_SCHEMA,
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


def test_env_ppo_backend_clear_cashout_exposes_exact_generated_first_shop():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed="CLEAR")
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    _, reward, terminated, truncated, _ = environment.step(
        EnvAction.from_alias("SELECT_BLIND")
    )

    assert (reward, terminated, truncated) == (0.0, False, False)
    assert environment.frame.status is RunStatus.RUNNING
    assert environment.frame.owner is TurnOwner.AGENT
    assert environment.frame.state.phase == "SHOP"
    observation = environment.frame.encoded_observation()
    assert observation.shape == (PPO_TRAINING_CONTRACT.observation_size,)
    assert len(backend.run.public.shop_jokers) + len(
        backend.run.public.shop_consumables
    ) == 2
    assert len(backend.run.public.shop_vouchers) == 1
    assert len(backend.run.public.shop_boosters) == 2
    assert tuple(
        item.center_key
        for items in (
            backend.run.public.shop_jokers,
            backend.run.public.shop_consumables,
            backend.run.public.shop_vouchers,
            backend.run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_droll",
        "c_tower",
        "v_directors_cut",
        "p_buffoon_normal_1",
        "p_celestial_normal_4",
    )
    assert all(
        item.discovered is False
        for items in (
            backend.run.public.shop_jokers,
            backend.run.public.shop_consumables,
            backend.run.public.shop_vouchers,
            backend.run.public.shop_boosters,
        )
        for item in items
    )

    actions = environment.legal_actions()
    assert EnvAction.from_alias("END_SHOP") in actions
    assert EnvAction.from_alias("REROLL_SHOP") in actions
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) in actions
    assert all(action.alias != "OPEN_PACK" for action in actions)
    assert all(action.alias != "BUY_VOUCHER" for action in actions)
    assert legal_action_mask(actions).values[action_index(EnvAction.from_alias("END_SHOP"))]

    snapshot = environment.serialize()
    restored = _environment()
    restored.restore(snapshot)
    assert restored.frame.encoded_observation().values == observation.values
    assert restored.serialize() == snapshot
    assert restored.legal_actions() == actions


def test_env_ppo_backend_acquires_generated_droll_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed="CLEAR")
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money

    assert (
        backend.run.public.shop_jokers[0].center_key,
        backend.run.public.shop_jokers[0].base_cost,
        backend.run.public.shop_jokers[0].price,
        backend.run.public.shop_jokers[0].discovered,
    ) == ("j_droll", 4, 4, False)
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is DrollJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_droll") is True
    assert "j_droll" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_odd_todd_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=91)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_gros_michel", 5, 5, False),
        ("j_odd_todd", 4, 4, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is OddToddJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_odd_todd") is True
    assert "j_odd_todd" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_even_steven_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=40)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_gros_michel", 5, 5, False),
        ("j_even_steven", 4, 4, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is EvenStevenJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_even_steven") is True
    assert "j_even_steven" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_devious_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=44)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_rocket", 6, 6, False),
        ("j_devious", 4, 4, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is DeviousJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_devious") is True
    assert "j_devious" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_gluttonous_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=9)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_gluttenous_joker", 5, 5, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is GluttonousJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_gluttenous_joker") is True
    assert "j_gluttenous_joker" in (
        backend.run.tag_profile_state.discovered_center_keys
    )
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_scholar_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=27)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_droll", 4, 4, False),
        ("j_scholar", 4, 4, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is ScholarJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_scholar") is True
    assert "j_scholar" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_blue_joker_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=28)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_clever", 4, 4, False),
        ("j_blue_joker", 5, 5, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is BlueJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_blue_joker") is True
    assert "j_blue_joker" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_jolly_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=23)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_jolly", 3, 3, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)

    assert backend.run.public.money == before_money - 3
    assert type(backend.run.public.jokers[0]) is JollyJoker
    assert backend.run.public.jokers[0].sell_cost == 1
    assert backend.run.generated_center_discovered("j_jolly") is True
    assert "j_jolly" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_sly_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=29)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_madness", 7, 7, False),
        ("j_sly", 3, 3, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 3
    assert type(backend.run.public.jokers[0]) is SlyJoker
    assert backend.run.public.jokers[0].sell_cost == 1
    assert backend.run.generated_center_discovered("j_sly") is True
    assert "j_sly" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_wily_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=17)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_erosion", 6, 6, False),
        ("j_wily", 4, 4, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is WilyJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_wily") is True
    assert "j_wily" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_abstract_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=311)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_abstract", 4, 4, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is AbstractJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_abstract") is True
    assert "j_abstract" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_photograph_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=61)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_photograph", 5, 5, False),
        ("j_trading", 6, 6, False),
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is PhotographJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_photograph") is True
    assert "j_photograph" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_half_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=12)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_half", 5, 5, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is HalfJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_half") is True
    assert "j_half" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_mystic_summit_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=11)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_mystic_summit", 5, 5, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is MysticSummitJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_mystic_summit") is True
    assert "j_mystic_summit" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_banner_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=31)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_8_ball", 5, 5, False),
        ("j_banner", 5, 5, False),
    )
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in (
        environment.legal_actions()
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is BannerJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_banner") is True
    assert "j_banner" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_scary_face_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=13)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_faceless", 4, 4, False),
        ("j_scary_face", 4, 4, False),
    )
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in (
        environment.legal_actions()
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is ScaryFaceJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_scary_face") is True
    assert "j_scary_face" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_walkie_talkie_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=77)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_walkie_talkie", 4, 4, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is WalkieTalkieJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_walkie_talkie") is True
    assert "j_walkie_talkie" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_smiley_face_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=57)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_smiley", 4, 4, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is SmileyFaceJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_smiley") is True
    assert "j_smiley" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_raised_fist_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=15)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_raised_fist", 5, 5, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 5
    assert type(backend.run.public.jokers[0]) is RaisedFistJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_raised_fist") is True
    assert "j_raised_fist" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 3


def test_env_ppo_backend_acquires_generated_clever_joker_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=19)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 1})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_drunkard", 4, 4, False),
        ("j_clever", 4, 4, False),
    )
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in (
        environment.legal_actions()
    )
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is CleverJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_clever") is True
    assert "j_clever" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_mad_joker_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=96)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_mad", 4, 4, False),)
    assert buy in environment.legal_actions()
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is MadJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_mad") is True
    assert "j_mad" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_acquires_generated_zany_joker_and_discovers_its_center():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=78)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    before_money = backend.run.public.money
    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (
        ("j_zany", 4, 4, False),
        ("j_ride_the_bus", 6, 6, False),
    )
    assert buy in environment.legal_actions()
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 1}) not in (
        environment.legal_actions()
    )
    environment.step(buy)
    assert backend.run.public.money == before_money - 4
    assert type(backend.run.public.jokers[0]) is ZanyJoker
    assert backend.run.public.jokers[0].sell_cost == 2
    assert backend.run.generated_center_discovered("j_zany") is True
    assert "j_zany" in backend.run.tag_profile_state.discovered_center_keys
    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    environment.step(sell)
    assert backend.run.public.money == before_money - 2


def test_env_ppo_backend_exposes_and_executes_exact_paid_shop_reroll():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed="PPO-REROLL-BRIDGE")
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    action = EnvAction.from_alias("REROLL_SHOP")
    before_money = backend.run.public.money
    before_cost = backend.run.reroll_cost
    before_main = tuple(backend.run.public.shop_jokers) + tuple(
        backend.run.public.shop_consumables
    )
    before_boosters = tuple(backend.run.public.shop_boosters)
    before_vouchers = tuple(backend.run.public.shop_vouchers)

    assert action in environment.legal_actions()
    _, reward, terminated, truncated, _ = environment.step(action)

    assert (reward, terminated, truncated) == (0.0, False, False)
    assert backend.run.public.money == before_money - before_cost
    assert backend.run.reroll_cost == before_cost + 1
    assert tuple(backend.run.public.shop_jokers) + tuple(
        backend.run.public.shop_consumables
    ) != before_main
    assert tuple(backend.run.public.shop_boosters) == before_boosters
    assert tuple(backend.run.public.shop_vouchers) == before_vouchers
    assert environment.frame.state.phase == "SHOP"
    assert backend.run.public.money < backend.run.reroll_cost
    assert action not in environment.legal_actions()


def test_env_ppo_backend_exposes_exact_generated_base_joker_buy_and_sale():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=225)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert tuple(
        (item.center_key, item.base_cost, item.price, item.discovered)
        for item in backend.run.public.shop_jokers
    ) == (("j_joker", 2, 2, True),)
    assert buy in environment.legal_actions()
    assert legal_action_mask(environment.legal_actions()).values[
        action_index(buy)
    ] is True
    before_money = backend.run.public.money
    before_mult = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=backend.run.public,
    ).mult

    _, reward, terminated, truncated, _ = environment.step(buy)

    assert (reward, terminated, truncated) == (0.0, False, False)
    assert backend.run.public.money == before_money - 2
    assert backend.run.public.shop_jokers == []
    assert len(backend.run.public.jokers) == 1
    joker = backend.run.public.jokers[0]
    assert type(joker) is FlatMultJoker
    assert (joker.mult, joker.cost, joker.sell_cost) == (4, 2, 1)
    assert BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=backend.run.public,
    ).mult == before_mult + 4

    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in environment.legal_actions()
    assert legal_action_mask(environment.legal_actions()).values[
        action_index(sell)
    ] is True
    environment.step(sell)
    assert backend.run.public.money == before_money - 1
    assert backend.run.public.jokers == []


def test_env_ppo_backend_replays_first_shop_big_blind_and_later_shop_exactly():
    backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=0)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000
    environment.step(EnvAction.from_alias("SELECT_BLIND"))

    first_shop_snapshot = environment.serialize()
    assert tuple(
        item.center_key
        for items in (
            backend.run.public.shop_jokers,
            backend.run.public.shop_consumables,
            backend.run.public.shop_vouchers,
            backend.run.public.shop_boosters,
        )
        for item in items
    ) == (
        "c_jupiter",
        "c_heirophant",
        "v_wasteful",
        "p_buffoon_normal_1",
        "p_standard_normal_3",
    )
    first_boundary = PPORolloutBoundary.from_frame(environment.frame)
    assert first_boundary.blind_requirement is None

    replay_backend = PPOHeadlessBackend(_OneCardTacticalPolicy())
    replay = BalatroHeadlessEnvironment(replay_backend)
    replay.restore(first_shop_snapshot)
    for current, current_backend in (
        (environment, backend),
        (replay, replay_backend),
    ):
        current.step(EnvAction.from_alias("END_SHOP"))
        run = current_backend.run
        assert current.frame.state.phase == "BLIND_SELECT"
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 450
        assert current.frame.state.blind.reward == 4
        assert run.blind_progression_state.small_status == "Defeated"
        assert run.blind_progression_state.big_status == "Select"
        assert run.blind_progression_state.blind_on_deck == "Big"
        assert current.legal_actions() == (EnvAction.from_alias("SELECT_BLIND"),)
        current.step(EnvAction.from_alias("SELECT_BLIND"))

    assert replay.serialize() == environment.serialize()
    assert replay.frame.encoded_observation().values == (
        environment.frame.encoded_observation().values
    )
    run = backend.run
    assert (run.public.phase, run.public.round, run.public.money) == ("SHOP", 2, 19)
    assert run.blind_progression_state.big_status == "Defeated"
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_ice_cream",
        "j_faceless",
        "v_planet_merchant",
        "p_buffoon_normal_2",
        "p_celestial_mega_1",
    )
    assert all(
        item.discovered is False
        for items in (
            run.public.shop_jokers,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    )
    actions = environment.legal_actions()
    assert actions == (
        EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
    )
    mask = legal_action_mask(actions)
    assert sum(mask.values) == 3
    assert mask.values[action_index(actions[0])] is True
    assert all(action.alias != "OPEN_PACK" for action in actions)
    later_boundary = PPORolloutBoundary.from_frame(environment.frame)
    assert later_boundary.blind_requirement is None

    for current, current_backend in (
        (environment, backend),
        (replay, replay_backend),
    ):
        current.step(EnvAction.from_alias("END_SHOP"))
        run = current_backend.run
        assert current.frame.state.phase == "BLIND_SELECT"
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 600
        assert current.frame.state.blind.reward == 5
        assert current.frame.state.boss_name == "The Psychic"
        assert run.blind_progression_state.boss_status == "Select"
        assert run.blind_progression_state.blind_on_deck == "Boss"
        assert run.boss_selection_state.usage_counts["bl_psychic"] == 1
        assert current.legal_actions() == (EnvAction.from_alias("SELECT_BLIND"),)

    assert replay.serialize() == environment.serialize()
    boss_boundary = PPORolloutBoundary.from_frame(environment.frame)
    assert boss_boundary.blind_requirement == 600.0
    _, reward, terminated, truncated, _ = environment.step(
        EnvAction.from_alias("SELECT_BLIND")
    )
    assert (reward, terminated, truncated) == (-1.0, True, False)
    assert environment.frame.state.score == 0
    assert environment.frame.state.hands_remaining == 0


def test_env_ppo_sparse_terminal_reward_contract_is_exact():
    assert sparse_terminal_reward(RunStatus.RUNNING) == 0.0
    assert sparse_terminal_reward(RunStatus.LOSS) == -1.0
    assert sparse_terminal_reward(RunStatus.ANTE_8_WIN) == 1.0
    with pytest.raises(TypeError):
        sparse_terminal_reward("LOSS")


def test_env_ppo_backend_resolves_supported_boss_into_exact_next_ante_shop():
    backend = PPOHeadlessBackend(_FiveCardTacticalPolicy())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=24)
    backend.run.public.hand_levels["HIGH_CARD"] = 1000

    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    environment.step(EnvAction.from_alias("END_SHOP"))
    environment.step(EnvAction.from_alias("SELECT_BLIND"))
    environment.step(EnvAction.from_alias("END_SHOP"))
    environment.step(EnvAction.from_alias("SELECT_BLIND"))

    run = backend.run
    assert (run.public.phase, run.public.ante, run.public.round) == ("SHOP", 2, 3)
    assert run.blind_progression_state.blind_on_deck == "Small"
    assert run.blind_progression_state.small_status == "Upcoming"
    assert run.blind_progression_state.boss_status == "Upcoming"
    assert run.blind_progression_state.small_tag == "tag_skip"
    assert run.blind_progression_state.big_tag == "tag_voucher"
    assert run.blind_progression_state.boss_name == "The Psychic"
    assert run.boss_selection_state.usage_counts["bl_hook"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 2
    assert run.tag_profile_state.discovered_center_keys == frozenset({"j_joker"})
    assert run.public.money == 24
    assert len(run.public.shop_vouchers) == 1
    assert len(run.public.shop_boosters) == 2
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_mad",
        "c_pluto",
        "v_wasteful",
        "p_standard_normal_1",
        "p_arcana_jumbo_1",
    )

    snapshot = environment.serialize()
    restored = BalatroHeadlessEnvironment(PPOHeadlessBackend(_FiveCardTacticalPolicy()))
    restored.restore(snapshot)
    assert restored.serialize() == snapshot
    assert restored.frame.encoded_observation() == environment.frame.encoded_observation()

    expected_actions = (
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
        EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}),
        EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
    )
    assert environment.legal_actions() == expected_actions
    assert restored.legal_actions() == expected_actions

    incomplete_backend = PPOHeadlessBackend(_FiveCardTacticalPolicy())
    incomplete = BalatroHeadlessEnvironment(incomplete_backend)
    incomplete.restore(snapshot)
    incomplete_backend.run.blind_progression_state.small_tag = None
    assert EnvAction.from_alias("END_SHOP") not in incomplete.legal_actions()
    before = incomplete.serialize()
    with pytest.raises(ValueError, match="illegal action"):
        incomplete.step(EnvAction.from_alias("END_SHOP"))
    assert incomplete.serialize() == before

    for current in (environment, restored):
        current.step(EnvAction.from_alias("END_SHOP"))
        state = current.frame.state
        assert state.phase == "BLIND_SELECT"
        assert state.ante == 2
        assert state.blind.type is BlindType.SMALL
        assert state.blind.requirement == 800
        assert state.blind.reward == 3
        assert state.blind.tag_key == "tag_skip"
        assert state.boss_name is None
        assert current.legal_actions() == (EnvAction.from_alias("SELECT_BLIND"),)
        for hand_name in state.hand_levels:
            state.hand_levels[hand_name] = 1000

    assert restored.serialize() == environment.serialize()
    assert restored.frame.encoded_observation() == environment.frame.encoded_observation()

    for current in (environment, restored):
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 1200
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 1600
        assert current.frame.state.boss_name == "The Psychic"

    assert restored.serialize() == environment.serialize()
    psychic_snapshot = environment.serialize()

    one_card = _environment(_OneCardTacticalPolicy())
    one_card.restore(psychic_snapshot)
    _, reward, terminated, truncated, _ = one_card.step(
        EnvAction.from_alias("SELECT_BLIND")
    )
    assert (reward, terminated, truncated) == (-1.0, True, False)
    assert one_card.frame.state.score == 0
    assert one_card.frame.state.hands_remaining == 0

    for current in (environment, restored):
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 3
        assert current.frame.state.round == 6
        assert current.frame.state.money == 59
        assert current.frame.status is RunStatus.RUNNING

    assert restored.serialize() == environment.serialize()
    assert restored.frame.encoded_observation() == environment.frame.encoded_observation()
    run = backend.run
    assert run.blind_progression_state.small_tag == "tag_standard"
    assert run.blind_progression_state.big_tag == "tag_top_up"
    assert run.blind_progression_state.boss_name == "The Pillar"
    assert run.boss_selection_state.usage_counts["bl_psychic"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 3
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_space",
        "j_banner",
        "v_magic_trick",
        "p_arcana_normal_3",
        "p_buffoon_normal_2",
    )
    assert not any(
        card.played_this_ante
        for card in run.require_playing_card_order()
    )

    for current in (environment, restored):
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 2000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 3000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 4000
        assert current.frame.state.boss_name == "The Pillar"

    assert restored.serialize() == environment.serialize()
    assert sum(
        card.played_this_ante
        for card in backend.run.require_playing_card_order()
    ) == 9
    assert all(
        card.played_this_ante_observed
        for card in backend.run.require_playing_card_order()
    )
    pillar_snapshot = environment.serialize()
    pillar_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    pillar_restored.restore(pillar_snapshot)
    assert pillar_restored.serialize() == pillar_snapshot
    assert pillar_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    for current in (environment, restored, pillar_restored):
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 4
        assert current.frame.state.round == 9
        assert current.frame.state.money == 95
        assert current.frame.status is RunStatus.RUNNING

    assert restored.serialize() == environment.serialize()
    assert pillar_restored.serialize() == environment.serialize()
    assert restored.frame.encoded_observation() == environment.frame.encoded_observation()
    run = backend.run
    assert run.blind_progression_state.small_tag == "tag_investment"
    assert run.blind_progression_state.big_tag == "tag_orbital"
    assert run.blind_progression_state.boss_name == "The Arm"
    assert run.boss_selection_state.usage_counts["bl_pillar"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 4
    assert not any(card.debuffed for card in run.require_playing_card_order())
    assert not any(
        card.played_this_ante
        for card in run.require_playing_card_order()
    )
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_vagabond",
        "j_8_ball",
        "v_paint_brush",
        "p_buffoon_normal_1",
        "p_arcana_normal_1",
    )

    for current in (environment, restored, pillar_restored):
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 5000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 7500
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 10_000
        assert current.frame.state.boss_name == "The Arm"

    assert restored.serialize() == environment.serialize()
    assert pillar_restored.serialize() == environment.serialize()
    assert sum(
        card.played_this_ante
        for card in backend.run.require_playing_card_order()
    ) == 10
    arm_snapshot = environment.serialize()
    arm_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    arm_restored.restore(arm_snapshot)
    assert arm_restored.serialize() == arm_snapshot
    assert arm_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    for current in (environment, restored, pillar_restored, arm_restored):
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 5
        assert current.frame.state.round == 12
        assert current.frame.state.money == 131
        assert current.frame.state.hand_levels["PAIR"] == 999
        assert current.frame.status is RunStatus.RUNNING

    assert restored.serialize() == environment.serialize()
    assert pillar_restored.serialize() == environment.serialize()
    assert arm_restored.serialize() == environment.serialize()
    run = backend.run
    assert all(
        level == (999 if hand_name == "PAIR" else 1000)
        for hand_name, level in run.public.hand_levels.items()
    )
    assert run.blind_progression_state.small_tag == "tag_garbage"
    assert run.blind_progression_state.big_tag == "tag_investment"
    assert run.blind_progression_state.boss_name == "The Fish"
    assert run.boss_selection_state.usage_counts["bl_arm"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 5
    assert not any(
        card.played_this_ante
        for card in run.require_playing_card_order()
    )
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_gros_michel",
        "c_strength",
        "v_tarot_merchant",
        "p_arcana_normal_1",
        "p_arcana_normal_3",
    )

    five_card_paths = (environment, restored, pillar_restored, arm_restored)
    for current in five_card_paths:
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 11_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 16_500
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 22_000
        assert current.frame.state.boss_name == "The Fish"

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    fish_snapshot = environment.serialize()
    fish_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    fish_restored.restore(fish_snapshot)
    assert fish_restored.serialize() == fish_snapshot
    assert fish_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    recording_policy = _RecordingOneCardTacticalPolicy()
    hidden_loss = BalatroHeadlessEnvironment(PPOHeadlessBackend(recording_policy))
    hidden_loss.restore(fish_snapshot)
    hidden_loss._backend.run.public.hand_levels["HIGH_CARD"] = 1
    _, reward, terminated, truncated, _ = hidden_loss.step(
        EnvAction.from_alias("SELECT_BLIND")
    )
    assert (reward, terminated, truncated) == (-1.0, True, False)
    assert hidden_loss.frame.state.score == 60
    assert hidden_loss.frame.state.hands_remaining == 0
    assert len(recording_policy.hands) == 4
    assert not any(face_down for face_down, _, _ in recording_policy.hands[0])
    assert all(
        any(face_down for face_down, _, _ in hand)
        for hand in recording_policy.hands[1:]
    )
    assert all(
        rank == suit == "?"
        for hand in recording_policy.hands[1:]
        for face_down, rank, suit in hand
        if face_down
    )

    five_card_paths = (*five_card_paths, fish_restored)
    for current in five_card_paths:
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 6
        assert current.frame.state.round == 15
        assert current.frame.state.money == 167
        assert current.frame.status is RunStatus.RUNNING

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    run = backend.run
    assert run.blind_progression_state.small_tag == "tag_standard"
    assert run.blind_progression_state.big_tag == "tag_boss"
    assert run.blind_progression_state.boss_name == "The Mouth"
    assert run.boss_selection_state.usage_counts["bl_fish"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 6
    assert not any(card.face_down for card in run.require_playing_card_order())
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_raised_fist",
        "j_credit_card",
        "v_paint_brush",
        "p_standard_normal_1",
        "p_buffoon_normal_2",
    )

    for current in five_card_paths:
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 20_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 30_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 40_000
        assert current.frame.state.boss_name == "The Mouth"
        assert current.frame.state.boss_blind_only_hand is None
        assert current.frame.state.boss_blind_state_observed is False

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    mouth_snapshot = environment.serialize()
    mouth_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    mouth_restored.restore(mouth_snapshot)
    assert mouth_restored.serialize() == mouth_snapshot
    assert mouth_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    five_card_paths = (*five_card_paths, mouth_restored)
    for current in five_card_paths:
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 7
        assert current.frame.state.round == 18
        assert current.frame.state.money == 203
        assert current.frame.state.boss_blind_only_hand is None
        assert current.frame.state.boss_blind_state_observed is False
        assert current.frame.status is RunStatus.RUNNING

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    run = backend.run
    assert run.blind_progression_state.small_tag == "tag_meteor"
    assert run.blind_progression_state.big_tag == "tag_handy"
    assert run.blind_progression_state.boss_name == "The Needle"
    assert run.boss_selection_state.usage_counts["bl_mouth"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 7
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_burglar",
        "c_jupiter",
        "v_paint_brush",
        "p_celestial_normal_4",
        "p_celestial_normal_3",
    )

    for current in five_card_paths:
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 35_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 52_500
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 70_000
        assert current.frame.state.boss_name == "The Needle"
        assert current._backend.run.boss_hands_sub is None
        assert current.frame.state.hands_remaining == 4

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    needle_snapshot = environment.serialize()
    needle_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    needle_restored.restore(needle_snapshot)
    assert needle_restored.serialize() == needle_snapshot
    assert needle_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    needle_loss = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    needle_loss.restore(needle_snapshot)
    for hand_name in needle_loss.frame.state.hand_levels:
        needle_loss._backend.run.public.hand_levels[hand_name] = 1
    _, reward, terminated, truncated, _ = needle_loss.step(
        EnvAction.from_alias("SELECT_BLIND")
    )
    assert (reward, terminated, truncated) == (-1.0, True, False)
    assert needle_loss.frame.state.hands_remaining == 0
    assert needle_loss._backend.run.boss_hands_sub == 3

    five_card_paths = (*five_card_paths, needle_restored)
    for current in five_card_paths:
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.ante == 8
        assert current.frame.state.round == 21
        assert current.frame.state.money == 236
        assert current._backend.run.boss_hands_sub is None
        assert current.frame.status is RunStatus.RUNNING

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    run = backend.run
    assert run.blind_progression_state.small_tag == "tag_investment"
    assert run.blind_progression_state.big_tag == "tag_voucher"
    assert run.blind_progression_state.boss_name == "Verdant Leaf"
    assert run.boss_selection_state.usage_counts["bl_needle"] == 1
    assert sum(run.boss_selection_state.usage_counts.values()) == 8
    assert tuple(
        item.center_key
        for items in (
            run.public.shop_jokers,
            run.public.shop_consumables,
            run.public.shop_vouchers,
            run.public.shop_boosters,
        )
        for item in items
    ) == (
        "j_droll",
        "j_scary_face",
        "v_hieroglyph",
        "p_arcana_jumbo_2",
        "p_standard_normal_4",
    )

    for current in five_card_paths:
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.SMALL
        assert current.frame.state.blind.requirement == 50_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.money == 247
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BIG
        assert current.frame.state.blind.requirement == 75_000
        current.step(EnvAction.from_alias("SELECT_BLIND"))
        assert current.frame.state.phase == "SHOP"
        assert current.frame.state.money == 259
        current.step(EnvAction.from_alias("END_SHOP"))
        assert current.frame.state.blind.type is BlindType.BOSS
        assert current.frame.state.blind.requirement == 100_000
        assert current.frame.state.boss_name == "Verdant Leaf"

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    verdant_snapshot = environment.serialize()
    verdant_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    verdant_restored.restore(verdant_snapshot)
    assert verdant_restored.serialize() == verdant_snapshot
    assert verdant_restored.frame.encoded_observation() == (
        environment.frame.encoded_observation()
    )

    five_card_paths = (*five_card_paths, verdant_restored)
    for current in five_card_paths:
        _, reward, terminated, truncated, _ = current.step(
            EnvAction.from_alias("SELECT_BLIND")
        )
        assert (reward, terminated, truncated) == (1.0, True, False)
        assert current.frame.status is RunStatus.ANTE_8_WIN
        assert current.frame.owner is TurnOwner.TERMINAL
        assert current.frame.state.phase == "ROUND_EVAL"
        assert current.frame.state.ante == 8
        assert current.frame.state.round == 24
        assert current.frame.state.money == 259
        assert current.frame.state.score == 9_995_000
        assert current.legal_actions() == ()
        assert current._backend.run.blind_progression_state.boss_status == "Current"
        assert all(
            card.debuffed
            for card in current._backend.run.require_playing_card_order()
        )

    assert all(current.serialize() == environment.serialize() for current in five_card_paths)
    terminal_snapshot = environment.serialize()
    terminal_restored = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(_FiveCardTacticalPolicy())
    )
    terminal_restored.restore(terminal_snapshot)
    assert terminal_restored.serialize() == terminal_snapshot
    assert terminal_restored.frame.status is RunStatus.ANTE_8_WIN
    assert terminal_restored.frame.owner is TurnOwner.TERMINAL
    assert terminal_restored.legal_actions() == ()


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


def test_env_ppo_collector_binds_progress_reward_contract_and_rollout_schema():
    training_run = PPOTrainingRun.from_seed(
        "PROGRESS-COLLECT", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    environment = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(
            _OneCardTacticalPolicy(),
            reward_contract=PPO_PROGRESS_REWARD_CONTRACT,
        )
    )

    episode = collect_complete_ppo_episode(
        environment,
        training_run,
        episode_index=0,
        policy=lambda observation, mask: _ppo_output(),
    )

    assert episode.schema_version == PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA
    assert episode.training_run.contract_sha256 == PPO_PROGRESS_TRAINING_CONTRACT.sha256
    assert episode.rewards == (-1.0,)
    assert episode.status is RunStatus.LOSS
    payload = episode.as_dict()
    assert payload["schema_version"] == PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA
    assert (
        payload["training_run"]["contract_sha256"]
        == PPO_PROGRESS_TRAINING_CONTRACT.sha256
    )


@pytest.mark.parametrize(
    ("training_contract", "backend_reward_contract"),
    [
        (PPO_TRAINING_CONTRACT, PPO_PROGRESS_REWARD_CONTRACT),
        (PPO_PROGRESS_TRAINING_CONTRACT, PPO_REWARD_CONTRACT),
    ],
)
def test_env_ppo_collector_fails_closed_on_reward_contract_mismatch(
    training_contract, backend_reward_contract
):
    training_run = PPOTrainingRun.from_seed(
        "REWARD-MISMATCH", contract=training_contract
    )
    environment = BalatroHeadlessEnvironment(
        PPOHeadlessBackend(
            _OneCardTacticalPolicy(), reward_contract=backend_reward_contract
        )
    )

    with pytest.raises(PPOContractError, match="reset reward contract mismatch"):
        collect_complete_ppo_episode(
            environment,
            training_run,
            episode_index=0,
            policy=lambda observation, mask: _ppo_output(),
        )
