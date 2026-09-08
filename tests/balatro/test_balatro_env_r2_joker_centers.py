import pytest

from games.balatro.env.joker_centers import (
    VANILLA_JOKER_CENTERS,
    current_joker_pool_from_eligible_keys,
    joker_rarity_id,
    vanilla_joker_pool,
)


def test_env_r2_vanilla_joker_catalogue_is_complete_unique_and_contiguous():
    assert len(VANILLA_JOKER_CENTERS) == 150
    assert [center.order for center in VANILLA_JOKER_CENTERS] == list(range(1, 151))
    assert len({center.key for center in VANILLA_JOKER_CENTERS}) == 150


def test_env_r2_vanilla_joker_rarity_pool_counts_match_pinned_source():
    assert len(vanilla_joker_pool("Common")) == 61
    assert len(vanilla_joker_pool("Uncommon")) == 64
    assert len(vanilla_joker_pool("Rare")) == 20
    assert len(vanilla_joker_pool("Legendary")) == 5


def test_env_r2_vanilla_joker_pool_order_preserves_global_center_order():
    common = vanilla_joker_pool(1)
    uncommon = vanilla_joker_pool(2)
    rare = vanilla_joker_pool(3)
    legendary = vanilla_joker_pool(4)

    assert common[:5] == (
        "j_joker",
        "j_greedy_joker",
        "j_lusty_joker",
        "j_wrathful_joker",
        "j_gluttenous_joker",
    )
    assert common[-3:] == ("j_swashbuckler", "j_hanging_chad", "j_shoot_the_moon")

    assert uncommon[:4] == ("j_stencil", "j_four_fingers", "j_mime", "j_ceremonial")
    assert uncommon[-3:] == ("j_cartomancer", "j_astronomer", "j_bootstraps")

    assert rare[:4] == ("j_dna", "j_vagabond", "j_baron", "j_obelisk")
    assert rare[-3:] == ("j_brainstorm", "j_drivers_license", "j_burnt")

    assert legendary == (
        "j_caino",
        "j_triboulet",
        "j_yorick",
        "j_chicot",
        "j_perkeo",
    )


def test_env_r2_vanilla_joker_catalogue_pins_source_spellings_and_orders():
    by_order = {center.order: center for center in VANILLA_JOKER_CENTERS}

    assert (by_order[5].key, by_order[5].rarity) == ("j_gluttenous_joker", 1)
    assert (by_order[47].key, by_order[47].rarity) == ("j_burglar", 2)
    assert (by_order[102].key, by_order[102].rarity) == ("j_selzer", 2)
    assert (by_order[121].key, by_order[121].rarity) == ("j_ring_master", 2)
    assert (by_order[150].key, by_order[150].rarity) == ("j_perkeo", 4)


def test_env_r2_joker_rarity_parser_is_strict():
    assert joker_rarity_id("Common") == 1
    assert joker_rarity_id("Uncommon") == 2
    assert joker_rarity_id("Rare") == 3
    assert joker_rarity_id("Legendary") == 4

    with pytest.raises(ValueError, match="unsupported Joker rarity"):
        joker_rarity_id("common")
    with pytest.raises(ValueError, match="unsupported Joker rarity"):
        joker_rarity_id(0)
    with pytest.raises(TypeError, match="exact integer"):
        joker_rarity_id(True)


def test_env_r2_current_joker_pool_preserves_unavailable_positions():
    common = vanilla_joker_pool(1)
    eligible = {common[0], common[3], common[-1]}

    pool = current_joker_pool_from_eligible_keys(1, eligible)

    assert len(pool) == len(common)
    assert pool[0] == common[0]
    assert pool[1] == "UNAVAILABLE"
    assert pool[2] == "UNAVAILABLE"
    assert pool[3] == common[3]
    assert pool[-1] == common[-1]
    assert sum(value != "UNAVAILABLE" for value in pool) == 3


def test_env_r2_empty_joker_rarity_pool_uses_vanilla_joker_fallback():
    assert current_joker_pool_from_eligible_keys(1, set()) == ("j_joker",)
    assert current_joker_pool_from_eligible_keys(2, set()) == ("j_joker",)
    assert current_joker_pool_from_eligible_keys(3, set()) == ("j_joker",)
    assert current_joker_pool_from_eligible_keys(4, set()) == ("j_joker",)


def test_env_r2_current_joker_pool_rejects_inexact_eligibility():
    with pytest.raises(TypeError, match="collection"):
        current_joker_pool_from_eligible_keys(1, "j_joker")
    with pytest.raises(TypeError, match="only strings"):
        current_joker_pool_from_eligible_keys(1, {"j_joker", 7})
    with pytest.raises(ValueError, match="unknown vanilla Joker"):
        current_joker_pool_from_eligible_keys(1, {"j_not_real"})
