import pytest

from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.shop_reroll import reroll_base_main_shop
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.chaos_the_clown import ChaosTheClownJoker
from games.balatro.jokers.credit_card import CreditCardJoker
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


def _generated_run(seed="REROLL-SHOP"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.money = 20
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
    return generate_base_main_shop(
        HeadlessRunState(public=state, seed=seed)
    ).run


def test_env_r2_paid_reroll_charges_then_increments_cost_and_replaces_two_cards():
    run = _generated_run()
    old_items = tuple(run.public.shop_jokers) + tuple(run.public.shop_consumables)
    before_rng = run.rng_snapshot()

    result = reroll_base_main_shop(run)

    assert result.previous_cost == 5
    assert result.next_cost == 6
    assert result.run.reroll_cost == 6
    assert result.run.public.money == 15
    assert len(result.items) == 2
    assert len(result.run.public.shop_jokers) + len(result.run.public.shop_consumables) == 2
    assert result.run.rng_snapshot() != before_rng
    assert run.public.money == 20
    assert run.reroll_cost == 5
    assert tuple(run.public.shop_jokers) + tuple(run.public.shop_consumables) == old_items


def test_env_r2_paid_reroll_replay_is_deterministic():
    first = reroll_base_main_shop(_generated_run("REROLL-REPLAY"))
    second = reroll_base_main_shop(_generated_run("REROLL-REPLAY"))

    assert first.items == second.items
    assert first.run.public.money == second.run.public.money == 15
    assert first.run.reroll_cost == second.run.reroll_cost == 6
    assert first.run.rng_snapshot() == second.run.rng_snapshot()


def test_env_r2_paid_rerolls_progress_cost_one_dollar_each_time():
    first = reroll_base_main_shop(_generated_run("REROLL-COST"))
    second = reroll_base_main_shop(first.run)

    assert first.previous_cost == 5
    assert first.next_cost == 6
    assert second.previous_cost == 6
    assert second.next_cost == 7
    assert second.run.public.money == 9


def test_env_r2_paid_reroll_rejects_unaffordable_cost_without_mutation():
    run = _generated_run()
    run.public.money = 4
    before_rng = run.rng_snapshot()
    before_items = tuple(run.public.shop_jokers) + tuple(run.public.shop_consumables)

    with pytest.raises(HeadlessTransitionError, match="cannot afford"):
        reroll_base_main_shop(run)

    assert run.public.money == 4
    assert run.reroll_cost == 5
    assert run.rng_snapshot() == before_rng
    assert tuple(run.public.shop_jokers) + tuple(run.public.shop_consumables) == before_items


def test_env_r2_paid_reroll_rejects_free_reroll_and_bankruptcy_modifiers():
    run = _generated_run()
    run.public.jokers.append(ChaosTheClownJoker())
    with pytest.raises(HeadlessTransitionError, match="free-reroll"):
        reroll_base_main_shop(run)

    run = _generated_run()
    run.public.jokers.append(CreditCardJoker())
    with pytest.raises(HeadlessTransitionError, match="bankruptcy"):
        reroll_base_main_shop(run)


def test_env_r2_paid_reroll_rejects_incomplete_or_auxiliary_shop_areas():
    run = _generated_run()
    if run.public.shop_jokers:
        run.public.shop_jokers.pop()
    else:
        run.public.shop_consumables.pop()
    with pytest.raises(HeadlessTransitionError, match="complete current-capacity main shop"):
        reroll_base_main_shop(run)

    run = _generated_run()
    run.public.shop_boosters.append(object())
    with pytest.raises(HeadlessTransitionError, match="booster/voucher"):
        reroll_base_main_shop(run)
