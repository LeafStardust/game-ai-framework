import pytest

from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.round_end import apply_round_end_gros_michel_extinction
from games.balatro.env.serialization import restore_headless_run_state
from games.balatro.env.shop_generation_state import (
    record_gros_michel_extinction,
    restore_removed_shop_jokers_to_generation_pool,
    suppress_visible_shop_jokers_from_generation_pool,
)
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.jokers.gros_michel import GrosMichelJoker


def test_gros_michel_extinction_switches_generation_pool_across_restore():
    run = pristine_red_white_reset(48)
    before = run.serialize()
    result = record_gros_michel_extinction(run)
    restored = restore_headless_run_state(result.serialize())
    removed_offer = GeneratedShopJokerItem("j_gros_michel", 1, 5, None, 5)
    updated = restore_removed_shop_jokers_to_generation_pool(restored, (removed_offer,))

    assert run.serialize() == before
    assert updated.gros_michel_extinct is True
    records = {record["key"]: record for record in updated.public.joker_generation_pools["1"]}
    assert "j_gros_michel" not in records
    assert records["j_cavendish"]["cost"] == 4
    assert records["j_cavendish"]["yes_pool_flag"] == "gros_michel_extinct"
    assert updated.rng_snapshot() == run.rng_snapshot()


@pytest.mark.parametrize(
    "seed, debuffed, extinct",
    [(0, False, True), (2, False, False), (0, True, False)],
)
def test_round_end_gros_michel_rolls_seeded_extinction(seed, debuffed, extinct):
    run = pristine_red_white_reset(seed)
    joker = GrosMichelJoker()
    joker.center = "j_gros_michel"
    joker.rarity = 1
    joker.base_cost = 5
    joker.debuffed = debuffed
    run.require_joker_order_state().acquire(joker, run.public.jokers)
    run.public.jokers.append(joker)
    run = suppress_visible_shop_jokers_from_generation_pool(run, (joker,))
    expected_rng = run.copy().rng
    if not debuffed:
        expected_rng.random("gros_michel")

    result = apply_round_end_gros_michel_extinction(run)

    assert result.gros_michel_extinct is extinct
    assert len(result.public.jokers) == (0 if extinct else 1)
    assert result.rng.nodes == expected_rng.nodes
    result.require_joker_order_state()
