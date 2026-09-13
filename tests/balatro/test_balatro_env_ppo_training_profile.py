import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_SCHEMA
from games.balatro.env.ppo_training_profile import (
    PPO_TRAINING_PROFILE,
    PPO_TRAINING_PROFILE_SCHEMA,
    initialize_pristine_ppo_generation_authority,
    pristine_profile_discovery,
)
from games.balatro.env.shop_generation_state import eligible_joker_keys_from_state
from games.balatro.env.shop_inventory_generation import generate_normal_shop_inventory
from games.balatro.env.shop_consumable_generation_state import (
    eligible_consumable_records_from_state,
)
from games.balatro.env.shop_voucher_generation import voucher_pool_from_observed_state
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _uninitialized_pristine_run(seed="PROFILE"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 0
    state.money = 4
    state.blind = create_small_blind(300)
    state.blind.reward = 3
    state.vouchers_observed = True
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(
        public=state,
        seed=seed,
        blind_progression_state=BlindProgressionState(
            small_status="Select",
            big_status="Upcoming",
            boss_status="Upcoming",
            blind_on_deck="Small",
            blind_ante=1,
        ),
    )


def test_env_ppo_training_profile_contract_is_versioned_and_exact():
    assert PPO_TRAINING_PROFILE.schema == PPO_TRAINING_PROFILE_SCHEMA
    assert (PPO_TRAINING_PROFILE.deck, PPO_TRAINING_PROFILE.stake) == ("RED", "WHITE")
    assert PPO_TRAINING_PROFILE.unlock_policy == "PINNED_VANILLA_NEW_PROFILE_DEFAULTS"
    assert PPO_TRAINING_PROFILE.banned_center_keys == ()
    assert PPO_TRAINING_PROFILE.pool_flags == ()
    assert PPO_TRAINING_PROFILE.used_center_keys == ()
    assert PPO_TRAINING_PROFILE.played_secret_hands == ()
    assert PPO_TRAINING_PROFILE.first_shop_buffoon_variant == 1
    assert pristine_profile_discovery("j_joker") is True
    assert pristine_profile_discovery("j_greedy_joker") is False
    assert pristine_profile_discovery("c_fool") is False
    assert pristine_profile_discovery("v_overstock_norm") is False
    assert pristine_profile_discovery("p_buffoon_normal_1") is False
    with pytest.raises(HeadlessTransitionError, match="outside"):
        pristine_profile_discovery("j_modded")


def test_env_ppo_pristine_profile_installs_exact_source_ordered_catalogues():
    run = _uninitialized_pristine_run()
    before = run.rng_snapshot()
    initialized = initialize_pristine_ppo_generation_authority(run)

    assert initialized.rng_snapshot() == before
    assert run.public.joker_generation_pool_observed is False
    assert sum(
        len(values)
        for values in initialized.public.joker_generation_pools.values()
    ) == 101
    assert eligible_joker_keys_from_state(initialized, 1)[:3] == (
        "j_joker", "j_greedy_joker", "j_lusty_joker",
    )
    assert "j_steel_joker" not in eligible_joker_keys_from_state(initialized, 2)
    assert "j_cavendish" not in eligible_joker_keys_from_state(initialized, 1)
    assert eligible_joker_keys_from_state(initialized, 4) == ()

    tarot = eligible_consumable_records_from_state(initialized, "Tarot")
    planet = eligible_consumable_records_from_state(initialized, "Planet")
    assert (len(tarot), tarot[0]["key"], tarot[-1]["key"]) == (22, "c_fool", "c_world")
    assert (len(planet), planet[0]["key"], planet[-1]["key"]) == (9, "c_mercury", "c_pluto")

    voucher_pool = voucher_pool_from_observed_state(initialized)
    assert len(voucher_pool) == 32
    assert voucher_pool[:4] == (
        "v_overstock_norm", "UNAVAILABLE", "v_clearance_sale", "UNAVAILABLE",
    )
    assert voucher_pool[-2:] == ("v_paint_brush", "UNAVAILABLE")
    assert EnvStateFrame(initialized.public).encoded_observation().shape == (
        len(PUBLIC_OBSERVATION_SCHEMA.feature_names),
    )


def test_env_ppo_profile_rejects_nonpristine_or_existing_authority_atomically():
    run = _uninitialized_pristine_run("PROFILE-FAIL")
    run.public.money = 5
    before = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="pristine Red/White reset"):
        initialize_pristine_ppo_generation_authority(run)
    assert run.rng_snapshot() == before
    assert run.public.joker_generation_pools == {}

    initialized = initialize_pristine_ppo_generation_authority(
        _uninitialized_pristine_run("PROFILE-TWICE")
    )
    with pytest.raises(HeadlessTransitionError, match="already initialized"):
        initialize_pristine_ppo_generation_authority(initialized)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tarot_rate", 8.0),
        ("planet_rate", 8.0),
        ("joker_generation_edition_rate", 2.0),
    ],
)
def test_env_ppo_profile_rejects_nonpristine_generation_rates(field, value):
    run = _uninitialized_pristine_run("PROFILE-RATE")
    setattr(run.public, field, value)
    with pytest.raises(HeadlessTransitionError, match="rate"):
        initialize_pristine_ppo_generation_authority(run)


def test_env_ppo_reset_installs_profile_generation_and_discovery_authority():
    run = pristine_red_white_reset("PROFILE-RESET")
    assert run.public.joker_generation_pool_observed is True
    assert run.public.consumable_generation_pool_observed is True
    assert run.public.voucher_generation_pool_observed is True
    assert run.generated_center_discovered("j_joker") is True
    assert run.generated_center_discovered("c_fool") is False


def test_env_ppo_profile_drives_complete_first_shop_in_source_order():
    run = initialize_pristine_ppo_generation_authority(
        _uninitialized_pristine_run("PROFILE-SHOP")
    )
    run.public.phase = "SHOP"
    run.public.shop_active = True
    run.public.shop_inflation_observed = True
    run.public.shop_inflation = 0

    generated = generate_normal_shop_inventory(
        run,
        first_shop=True,
        first_buffoon_variant=PPO_TRAINING_PROFILE.first_shop_buffoon_variant,
        banned_booster_keys=PPO_TRAINING_PROFILE.banned_center_keys,
    )

    assert len(generated.main.items) == 2
    assert tuple(item.center_key for item in generated.main.items) == (
        "j_credit_card",
        "j_sixth_sense",
    )
    assert len(generated.run.public.shop_vouchers) == 1
    assert generated.run.public.shop_vouchers[0] == generated.voucher
    assert generated.voucher.center_key == "v_reroll_surplus"
    assert len(generated.boosters.items) == 2
    assert tuple(item.center_key for item in generated.boosters.items) == (
        "p_buffoon_normal_1",
        "p_arcana_normal_4",
    )
    assert tuple(item.discovered for item in generated.main.items) == (False, False)
    assert generated.voucher.discovered is False
    assert tuple(item.discovered for item in generated.boosters.items) == (False, False)
    nodes = generated.run.rng_snapshot()["nodes"]
    assert "Voucher" in nodes
    assert "shop_pack1" in nodes
