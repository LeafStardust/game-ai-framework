import pytest

from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
    current_consumable_pool_from_eligible_keys,
)


def test_env_r2_tarot_center_order_is_complete_and_pinned():
    assert len(VANILLA_TAROT_CENTER_ORDER) == 22
    assert VANILLA_TAROT_CENTER_ORDER[:4] == (
        "c_fool",
        "c_magician",
        "c_high_priestess",
        "c_empress",
    )
    assert VANILLA_TAROT_CENTER_ORDER[-4:] == (
        "c_moon",
        "c_sun",
        "c_judgement",
        "c_world",
    )
    assert len(set(VANILLA_TAROT_CENTER_ORDER)) == 22


def test_env_r2_planet_center_order_is_complete_and_pinned():
    assert VANILLA_PLANET_CENTER_ORDER == (
        "c_mercury",
        "c_venus",
        "c_earth",
        "c_mars",
        "c_jupiter",
        "c_saturn",
        "c_uranus",
        "c_neptune",
        "c_pluto",
        "c_planet_x",
        "c_ceres",
        "c_eris",
    )


def test_env_r2_consumable_pool_preserves_unavailable_positions():
    pool = current_consumable_pool_from_eligible_keys(
        "Tarot",
        {"c_fool", "c_empress", "c_world"},
    )

    assert len(pool) == 22
    assert pool[0] == "c_fool"
    assert pool[1] == "UNAVAILABLE"
    assert pool[3] == "c_empress"
    assert pool[-1] == "c_world"


def test_env_r2_consumable_pool_uses_vanilla_empty_fallbacks():
    assert current_consumable_pool_from_eligible_keys("Tarot", ()) == ("c_strength",)
    assert current_consumable_pool_from_eligible_keys("Planet", ()) == ("c_pluto",)


def test_env_r2_consumable_pool_rejects_unknown_or_invalid_keys():
    with pytest.raises(ValueError, match="unknown vanilla center"):
        current_consumable_pool_from_eligible_keys("Planet", {"c_not_a_planet"})
    with pytest.raises(TypeError, match="collection"):
        current_consumable_pool_from_eligible_keys("Tarot", "c_fool")
    with pytest.raises(ValueError, match="Tarot or Planet"):
        current_consumable_pool_from_eligible_keys("Spectral", ())
