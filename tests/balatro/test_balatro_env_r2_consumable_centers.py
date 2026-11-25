import pytest

from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_SPECTRAL_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
    current_consumable_pool_from_eligible_keys,
)
from games.balatro.env.consumable_generation import poll_seance_spectral_center
from games.balatro.env.rng import BalatroRNG


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
    with pytest.raises(ValueError, match="Tarot, Planet, or Spectral"):
        current_consumable_pool_from_eligible_keys("Voucher", ())


def test_env_r2_spectral_pool_keeps_hidden_center_positions_unavailable():
    pool = current_consumable_pool_from_eligible_keys(
        "Spectral", {"c_familiar", "c_ectoplasm", "c_cryptid"}
    )

    assert len(VANILLA_SPECTRAL_CENTER_ORDER) == len(pool) == 18
    assert VANILLA_SPECTRAL_CENTER_ORDER[-2:] == ("c_soul", "c_black_hole")
    assert {i: key for i, key in enumerate(pool) if key != "UNAVAILABLE"} == {
        0: "c_familiar",
        8: "c_ectoplasm",
        15: "c_cryptid",
    }


def test_env_r2_seance_polls_seeded_spectral_positions_and_ordered_retries():
    rng = BalatroRNG(48)

    assert poll_seance_spectral_center(rng, 2, {"c_cryptid"}) == ("c_cryptid", 5)
    assert list(rng.nodes) == [
        "Spectralsea2",
        *(f"Spectralsea2_resample{i}" for i in range(2, 7)),
    ]


def test_env_r2_seance_all_unavailable_polls_incantation_and_advances_base_node():
    rng = BalatroRNG(48)

    assert poll_seance_spectral_center(rng, 0, ()) == ("c_incantation", 0)
    assert list(rng.nodes) == ["Spectralsea0"]


@pytest.mark.parametrize("hidden", ["c_soul", "c_black_hole"])
def test_env_r2_seance_rejects_hidden_eligibility_before_rng(hidden):
    rng = BalatroRNG(48)

    with pytest.raises(ValueError, match="hidden Spectrals"):
        poll_seance_spectral_center(rng, 2, {hidden})
    assert rng.nodes == {}
