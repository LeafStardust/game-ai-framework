import pytest

from games.balatro.env.shop_consumable_items import (
    OrdinaryShopConsumableDescriptor,
    materialize_base_shop_consumable_descriptor,
)
from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.shop_inflation = 1
    state.shop_inflation_observed = True
    state.shop_discount_percent = 25
    state.shop_discount_percent_observed = True
    state.vouchers_observed = True
    state.vouchers = ["v_clearance_sale"]
    return HeadlessRunState(public=state, seed="PLANET-COST")


def test_env_r2_planet_multiplier_is_post_discount():
    # Vanilla: floor((3 + 1 + 0.5) * .75) == 3, then Planet doubles to 6.
    # Applying x2 before discount would produce 5 and is therefore observably wrong.
    assert vanilla_card_cost(
        3,
        edition=None,
        inflation=1,
        discount_percent=25,
        post_discount_multiplier=2,
    ) == 6


def test_env_r2_planet_materialization_doubles_after_discount_but_tarot_does_not():
    run = _run()

    planet_run, planet = materialize_base_shop_consumable_descriptor(
        OrdinaryShopConsumableDescriptor(
            run=run,
            card_type="Planet",
            center_key="c_pluto",
            base_cost=3,
            resamples=0,
        )
    )
    tarot_run, tarot = materialize_base_shop_consumable_descriptor(
        OrdinaryShopConsumableDescriptor(
            run=run,
            card_type="Tarot",
            center_key="c_strength",
            base_cost=3,
            resamples=0,
        )
    )

    assert planet.price == 6
    assert tarot.price == 3
    assert planet_run.public.shop_discount_percent == 25
    assert tarot_run.public.shop_inflation == 1
    assert run.public.shop_consumables == []


def test_env_r2_post_discount_multiplier_is_exact_positive_integer():
    for value in (0, -1, True, 1.5, "2"):
        with pytest.raises(HeadlessTransitionError):
            vanilla_card_cost(
                3,
                edition=None,
                inflation=0,
                discount_percent=0,
                post_discount_multiplier=value,
            )
