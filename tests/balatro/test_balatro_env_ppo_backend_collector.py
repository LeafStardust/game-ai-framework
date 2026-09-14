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
    assert all(action.alias != "OPEN_PACK" for action in actions)
    assert all(action.alias != "BUY_VOUCHER" for action in actions)
    assert legal_action_mask(actions).values[action_index(EnvAction.from_alias("END_SHOP"))]

    snapshot = environment.serialize()
    restored = _environment()
    restored.restore(snapshot)
    assert restored.frame.encoded_observation().values == observation.values
    assert restored.serialize() == snapshot
    assert restored.legal_actions() == actions


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
        EnvAction.from_alias("END_SHOP"),
    )
    mask = legal_action_mask(actions)
    assert sum(mask.values) == 2
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
        EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}),
        EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}),
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
