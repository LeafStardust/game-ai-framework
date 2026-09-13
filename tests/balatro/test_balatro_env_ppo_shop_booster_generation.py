import pytest

from games.balatro.env.shop_booster_generation import (
    VANILLA_BOOSTER_CENTERS,
    first_shop_buffoon_center,
    generate_first_normal_shop_boosters,
    generate_weighted_normal_shop_boosters,
    materialize_normal_shop_booster,
    poll_weighted_normal_shop_booster,
)
from games.balatro.env.shop_inventory_generation import (
    generate_normal_shop_without_voucher,
)
from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_SCHEMA
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.astronomer import AstronomerJoker
from games.balatro.state import BalatroState


def _shop_run(seed="BOOSTERS"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.vouchers_observed = True
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    return HeadlessRunState(public=state, seed=seed)


def _joker_record(rarity, key, cost):
    return {
        "rarity": rarity,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
    }


def _consumable_record(card_type, key):
    return {
        "type": card_type,
        "key": key,
        "cost": 3,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }


def _shop_with_generation_catalogues(seed="FULL-SHOP"):
    run = _shop_run(seed)
    run.public.joker_generation_pool_observed = True
    run.public.joker_generation_pools = {
        "1": [_joker_record(1, "j_joker", 2)],
        "2": [_joker_record(2, "j_stencil", 8)],
        "3": [_joker_record(3, "j_dna", 8)],
        "4": [_joker_record(4, "j_caino", 20)],
    }
    run.public.consumable_generation_pool_observed = True
    run.public.consumable_generation_pools = {
        "Tarot": [_consumable_record("Tarot", "c_strength")],
        "Planet": [_consumable_record("Planet", "c_pluto")],
    }
    return run


def test_env_ppo_booster_catalogue_matches_pinned_vanilla_order_and_weights():
    assert len(VANILLA_BOOSTER_CENTERS) == 32
    assert tuple(center.order for center in VANILLA_BOOSTER_CENTERS) == tuple(
        range(1, 33)
    )
    assert VANILLA_BOOSTER_CENTERS[0].center_key == "p_arcana_normal_1"
    assert VANILLA_BOOSTER_CENTERS[-1].center_key == "p_spectral_mega_1"
    assert sum(center.weight for center in VANILLA_BOOSTER_CENTERS) == pytest.approx(
        22.42
    )
    assert {
        (center.family, center.base_cost, center.pack_size, center.choices)
        for center in VANILLA_BOOSTER_CENTERS
        if "mega" in center.center_key
    } == {
        ("Arcana", 8, 5, 2),
        ("Celestial", 8, 5, 2),
        ("Standard", 8, 5, 2),
        ("Buffoon", 8, 4, 2),
        ("Spectral", 8, 4, 2),
    }


def test_env_ppo_weighted_boosters_fill_two_slots_deterministically():
    run = _shop_run("BOOSTER-REPLAY")
    before = run.rng_snapshot()

    first = generate_weighted_normal_shop_boosters(run)
    second = generate_weighted_normal_shop_boosters(_shop_run("BOOSTER-REPLAY"))

    assert first.items == second.items
    assert tuple(item.center_key for item in first.items) == (
        "p_celestial_jumbo_1",
        "p_celestial_jumbo_2",
    )
    assert first.run.rng_snapshot() == second.run.rng_snapshot()
    assert len(first.run.public.shop_boosters) == 2
    assert tuple(item.booster_position for item in first.items) == (1, 2)
    assert all(item.discovered is None for item in first.items)
    assert all(item.kind == "BOOSTER" for item in first.items)
    assert run.public.shop_boosters == []
    assert run.rng_snapshot() == before
    assert "shop_pack1" in first.run.rng_snapshot()["nodes"]


def test_env_ppo_generated_boosters_encode_without_inventing_discovery_state():
    generated = generate_weighted_normal_shop_boosters(_shop_run("ENCODE-BOOSTER"))
    encoded = EnvStateFrame(generated.run.public).encoded_observation()
    values = dict(zip(PUBLIC_OBSERVATION_SCHEMA.feature_names, encoded.values))

    assert values["shop.boosters.0.present"] == 1.0
    assert values["shop.boosters.0.base_cost"] == float(
        generated.items[0].base_cost
    )
    assert values["shop.boosters.0.price"] == float(generated.items[0].price)
    assert values["shop.boosters.0.discovered"] == -1.0


def test_env_ppo_first_shop_requires_exact_unkeyed_buffoon_variant_authority():
    run = _shop_run("FIRST-BOOSTER")
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="unkeyed RNG authority"):
        generate_first_normal_shop_boosters(
            run,
            first_buffoon_variant=0,
        )
    assert run.rng_snapshot() == before

    generated = generate_first_normal_shop_boosters(
        run,
        first_buffoon_variant=2,
    )
    direct_second = poll_weighted_normal_shop_booster(run)
    assert generated.items[0].center_key == "p_buffoon_normal_2"
    assert generated.items[1].center_key == "p_arcana_normal_2"
    assert generated.items[1].center_key == direct_second.center.center_key
    assert generated.run.rng_snapshot() == direct_second.run.rng_snapshot()


def test_env_ppo_first_shop_override_honors_source_ban_guard():
    with pytest.raises(HeadlessTransitionError, match="disabled.*bans"):
        first_shop_buffoon_center(
            1,
            banned_center_keys={"p_buffoon_normal_1"},
        )


def test_env_ppo_weighted_booster_poll_honors_exact_banned_pool():
    only_center = "p_spectral_mega_1"
    banned = {
        center.center_key
        for center in VANILLA_BOOSTER_CENTERS
        if center.center_key != only_center
    }

    result = poll_weighted_normal_shop_booster(
        _shop_run("BANNED-POOL"),
        banned_center_keys=banned,
    )

    assert result.center.center_key == only_center
    assert "shop_pack1" in result.run.rng_snapshot()["nodes"]

    run = _shop_run("EMPTY-BOOSTER-POOL")
    before = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="no eligible center"):
        poll_weighted_normal_shop_booster(
            run,
            banned_center_keys={
                center.center_key for center in VANILLA_BOOSTER_CENTERS
            },
        )
    assert run.rng_snapshot() == before


def test_env_ppo_booster_materialization_owns_discount_and_astronomer_price():
    run = _shop_run()
    run.public.vouchers = ["v_clearance_sale"]
    run.public.shop_discount_percent = 25
    jumbo_arcana = next(
        center for center in VANILLA_BOOSTER_CENTERS
        if center.center_key == "p_arcana_jumbo_1"
    )
    discounted = materialize_normal_shop_booster(
        run,
        jumbo_arcana,
        booster_position=1,
    )
    assert discounted.price == 4

    run.public.jokers.append(AstronomerJoker())
    celestial = next(
        center for center in VANILLA_BOOSTER_CENTERS
        if center.center_key == "p_celestial_normal_1"
    )
    free = materialize_normal_shop_booster(
        run,
        celestial,
        booster_position=1,
    )
    assert free.price == 0


def test_env_ppo_booster_generation_preflights_unsupported_state_before_rng():
    run = _shop_run()
    run.tags.append("Coupon")
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="active Tags"):
        generate_weighted_normal_shop_boosters(run)
    assert run.rng_snapshot() == before

    run = _shop_run()
    before = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="not pinned centers"):
        generate_weighted_normal_shop_boosters(
            run,
            banned_center_keys={"p_unknown"},
        )
    assert run.rng_snapshot() == before


def test_env_ppo_shop_composition_generates_main_then_first_shop_boosters():
    run = _shop_with_generation_catalogues("SOURCE-ORDER")
    before = run.rng_snapshot()

    result = generate_normal_shop_without_voucher(
        run,
        first_shop=True,
        first_buffoon_variant=1,
    )
    expected_main = generate_base_main_shop(run)
    expected_boosters = generate_first_normal_shop_boosters(
        expected_main.run,
        first_buffoon_variant=1,
    )

    assert result.main.items == expected_main.items
    assert result.boosters.items == expected_boosters.items
    assert result.run.rng_snapshot() == expected_boosters.run.rng_snapshot()
    assert len(result.run.public.shop_jokers) + len(
        result.run.public.shop_consumables
    ) == 2
    assert len(result.run.public.shop_boosters) == 2
    assert result.run.public.shop_vouchers == []
    assert run.rng_snapshot() == before


def test_env_ppo_shop_composition_rejects_missing_or_stale_first_shop_authority():
    run = _shop_with_generation_catalogues()
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="requires exact unkeyed"):
        generate_normal_shop_without_voucher(run, first_shop=True)
    with pytest.raises(HeadlessTransitionError, match="later shop cannot carry"):
        generate_normal_shop_without_voucher(
            run,
            first_shop=False,
            first_buffoon_variant=1,
        )
    assert run.rng_snapshot() == before
