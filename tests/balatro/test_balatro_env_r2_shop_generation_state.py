import pytest
from types import SimpleNamespace

from games.balatro.env.shop_generation_state import (
    eligible_joker_keys_from_state,
    joker_center_cost_from_state,
    restore_removed_shop_jokers_to_generation_pool,
    suppress_visible_shop_jokers_from_generation_pool,
)
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [
            {"rarity": 1, "key": "j_joker", "cost": 2},
            {"rarity": 1, "key": "j_greedy_joker", "cost": 5},
        ],
        "2": [],
        "3": [],
        "4": [],
    }
    return HeadlessRunState(public=state, seed="POOLKEYS")


def test_env_r2_shop_generation_state_reads_canonical_string_rarity_key():
    assert eligible_joker_keys_from_state(_run(), 1) == (
        "j_joker",
        "j_greedy_joker",
    )


def test_env_r2_shop_generation_state_returns_exact_selected_center_cost():
    run = _run()

    assert joker_center_cost_from_state(run, 1, "j_joker") == 2
    assert joker_center_cost_from_state(run, 1, "j_greedy_joker") == 5


def test_env_r2_shop_generation_state_rejects_invalid_center_cost():
    for bad_cost in (None, True, -1, 2.5, "2"):
        run = _run()
        run.public.joker_generation_pools["1"][0]["cost"] = bad_cost
        with pytest.raises(HeadlessTransitionError, match="invalid center cost"):
            eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_generation_state_rejects_noncanonical_integer_rarity_key():
    run = _run()
    run.public.joker_generation_pools = {
        1: [{"rarity": 1, "key": "j_joker", "cost": 2}],
    }

    with pytest.raises(HeadlessTransitionError, match="exact rarities 1 through 4"):
        eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_generation_state_rejects_unobserved_pool():
    run = _run()
    run.public.joker_generation_pool_observed = False

    with pytest.raises(HeadlessTransitionError, match="not authoritatively observed"):
        eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_generation_state_validates_all_rarities_before_selected_one():
    run = _run()
    run.public.joker_generation_pools["4"] = [
        {"rarity": 3, "key": "j_caino", "cost": 20},
    ]

    with pytest.raises(HeadlessTransitionError, match="rarity mismatch"):
        eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_generation_state_rejects_malformed_record_metadata():
    run = _run()
    run.public.joker_generation_pools["2"] = [
        {"rarity": 2, "key": "j_stencil", "cost": 8, "unlocked": "yes"},
    ]
    with pytest.raises(HeadlessTransitionError, match="invalid unlocked state"):
        eligible_joker_keys_from_state(run, 1)

    run = _run()
    run.public.joker_generation_pools["3"] = [
        {"rarity": 3, "key": "j_dna", "cost": 8, "no_pool_flag": ""},
    ]
    with pytest.raises(HeadlessTransitionError, match="invalid no_pool_flag"):
        eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_generation_state_rejects_duplicate_keys_across_catalogue():
    run = _run()
    run.public.joker_generation_pools["2"] = [
        {"rarity": 2, "key": "j_joker", "cost": 2},
    ]

    with pytest.raises(HeadlessTransitionError, match="duplicate center keys"):
        eligible_joker_keys_from_state(run, 1)


def test_env_r2_shop_joker_visibility_restores_then_suppresses_exact_pool_record():
    run = _run()
    run.public.phase = "SHOP"
    run.public.shop_active = True
    run.public.shop_inflation_observed = True
    run.public.shop_discount_percent_observed = True
    run.public.joker_generation_pools["1"] = [
        record
        for record in run.public.joker_generation_pools["1"]
        if record["key"] != "j_greedy_joker"
    ]
    removed = SimpleNamespace(
        center="j_greedy_joker",
        rarity="COMMON",
        base_cost=5,
        cost=5,
        edition=None,
    )

    restored = restore_removed_shop_jokers_to_generation_pool(run, (removed,))

    assert [record["key"] for record in restored.public.joker_generation_pools["1"]] == [
        "j_joker",
        "j_greedy_joker",
    ]
    assert restored.public.joker_generation_pools["1"][1]["cost"] == 5
    assert restored.public.joker_generation_pools["1"][1]["unlocked"] is True

    visible = GeneratedShopJokerItem("j_joker", 1, 2, None, 2)
    suppressed = suppress_visible_shop_jokers_from_generation_pool(restored, (visible,))
    assert [record["key"] for record in suppressed.public.joker_generation_pools["1"]] == [
        "j_greedy_joker",
    ]
