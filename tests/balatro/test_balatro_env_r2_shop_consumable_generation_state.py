import pytest

from games.balatro.env.shop_consumable_generation_state import (
    eligible_consumable_records_from_state,
    generate_ordinary_shop_consumable_descriptor_from_state,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _record(card_type: str, key: str, cost: int = 3, **extra):
    value = {
        "type": card_type,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }
    value.update(extra)
    return value


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 2
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [_record("Tarot", "c_strength")],
        "Planet": [_record("Planet", "c_pluto")],
    }
    return HeadlessRunState(public=state, seed="CANONICAL-CONSUMABLE")


def test_env_r2_canonical_consumable_pool_bridge_copies_exact_records():
    run = _run()

    records = eligible_consumable_records_from_state(run, "Tarot")

    assert records == (_record("Tarot", "c_strength"),)
    records[0]["cost"] = 99
    assert run.public.consumable_generation_pools["Tarot"][0]["cost"] == 3


def test_env_r2_canonical_consumable_pool_bridge_drives_identity_without_mutating_input_rng():
    run = _run()
    before = run.rng_snapshot()

    descriptor = generate_ordinary_shop_consumable_descriptor_from_state(run, "Planet")

    assert descriptor.center_key == "c_pluto"
    assert descriptor.base_cost == 3
    assert run.rng_snapshot() == before
    assert descriptor.run.rng_snapshot() != before


def test_env_r2_canonical_consumable_pool_bridge_requires_observation_marker():
    run = _run()
    run.public.consumable_generation_pool_observed = False

    with pytest.raises(HeadlessTransitionError, match="not authoritatively observed"):
        eligible_consumable_records_from_state(run, "Tarot")


def test_env_r2_canonical_consumable_pool_bridge_requires_both_catalogues_before_rng():
    run = _run()
    del run.public.consumable_generation_pools["Planet"]
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="exact Tarot and Planet"):
        generate_ordinary_shop_consumable_descriptor_from_state(run, "Tarot")

    assert run.rng_snapshot() == before


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda pools: pools["Planet"].append("bad"), "mapping"),
        (lambda pools: pools["Planet"][0].update(type="Tarot"), "type mismatch"),
        (lambda pools: pools["Planet"][0].update(cost=True), "center cost"),
        (
            lambda pools: pools["Planet"].append(_record("Planet", "c_strength")),
            "duplicate",
        ),
        (lambda pools: pools["Planet"][0].update(unlocked="yes"), "unlocked"),
        (lambda pools: pools["Planet"][0].update(softlock="yes"), "softlock"),
        (
            lambda pools: pools["Planet"][0].update(softlock=True, hand_type=None),
            "requires hand_type",
        ),
    ],
)
def test_env_r2_canonical_consumable_pool_bridge_validates_unselected_catalogue_before_rng(
    mutate, match
):
    run = _run()
    mutate(run.public.consumable_generation_pools)
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match=match):
        generate_ordinary_shop_consumable_descriptor_from_state(run, "Tarot")

    assert run.rng_snapshot() == before


def test_env_r2_canonical_consumable_generation_state_survives_public_copy():
    run = _run()

    copied = run.public.copy()

    assert copied.consumable_generation_pool_observed is True
    assert copied.consumable_generation_pools == run.public.consumable_generation_pools
    assert copied.consumable_generation_pools is not run.public.consumable_generation_pools
    copied.consumable_generation_pools["Tarot"][0]["cost"] = 8
    assert run.public.consumable_generation_pools["Tarot"][0]["cost"] == 3
