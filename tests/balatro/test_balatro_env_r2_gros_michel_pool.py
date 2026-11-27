from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.serialization import restore_headless_run_state
from games.balatro.env.shop_generation_state import (
    record_gros_michel_extinction,
    restore_removed_shop_jokers_to_generation_pool,
)
from games.balatro.env.shop_items import GeneratedShopJokerItem


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
