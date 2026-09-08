import pytest

from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _joker_record(rarity, key, cost):
    return {
        "rarity": rarity,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
    }


def _consumable_record(card_type, key, cost=3):
    return {
        "type": card_type,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }


def _run(seed="SHOP-COMPOSE"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [_joker_record(1, "j_joker", 2)],
        "2": [_joker_record(2, "j_stencil", 8)],
        "3": [_joker_record(3, "j_dna", 8)],
        "4": [_joker_record(4, "j_caino", 20)],
    }
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [_consumable_record("Tarot", "c_strength")],
        "Planet": [_consumable_record("Planet", "c_pluto")],
    }
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_main_shop_generates_exactly_two_items_and_keeps_input_isolated():
    run = _run()
    before_rng = run.rng_snapshot()

    generated = generate_base_main_shop(run)

    assert len(generated.items) == 2
    assert len(generated.run.public.shop_jokers) + len(generated.run.public.shop_consumables) == 2
    assert run.public.shop_jokers == []
    assert run.public.shop_consumables == []
    assert run.rng_snapshot() == before_rng
    assert generated.run.rng_snapshot() != before_rng


def test_env_r2_main_shop_is_replay_deterministic_for_same_seed_and_catalogues():
    first = generate_base_main_shop(_run("REPLAY-SHOP"))
    second = generate_base_main_shop(_run("REPLAY-SHOP"))

    assert first.items == second.items
    assert first.run.rng_snapshot() == second.run.rng_snapshot()
    assert first.run.public.shop_jokers == second.run.public.shop_jokers
    assert first.run.public.shop_consumables == second.run.public.shop_consumables


def test_env_r2_main_shop_preflights_consumable_catalogue_before_advancing_rng():
    run = _run()
    del run.public.consumable_generation_pools["Planet"]
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="exact Tarot and Planet"):
        generate_base_main_shop(run)

    assert run.rng_snapshot() == before
    assert run.public.shop_jokers == []
    assert run.public.shop_consumables == []


def test_env_r2_main_shop_preflights_joker_catalogue_before_advancing_rng():
    run = _run()
    del run.public.joker_generation_pools["4"]
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="rarities 1 through 4"):
        generate_base_main_shop(run)

    assert run.rng_snapshot() == before


def test_env_r2_main_shop_rejects_non_authoritative_pricing_before_rng():
    run = _run()
    run.public.shop_discount_percent_observed = False
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="discount percent is not authoritative"):
        generate_base_main_shop(run)

    assert run.rng_snapshot() == before


def test_env_r2_main_shop_rejects_existing_inventory():
    run = _run()
    run.public.shop_consumables.append(object())

    with pytest.raises(HeadlessTransitionError, match="ungenerated inventory"):
        generate_base_main_shop(run)
