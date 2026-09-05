import pytest

from games.balatro.env.shop_consumable_items import (
    OrdinaryShopConsumableDescriptor,
    materialize_base_shop_consumable_descriptor,
)
from games.balatro.env.shop_voucher_items import (
    OrdinaryShopVoucherDescriptor,
    materialize_normal_shop_voucher_descriptor,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    expected_shop_discount_percent_for_vouchers,
    shop_generation_vouchers_are_exact,
    shop_pricing_vouchers_are_exact,
)
from games.balatro.state import BalatroState


def _run(vouchers=(), *, discount=0, edition_rate=1.0):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.joker_generation_edition_rate = edition_rate
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = discount
    return HeadlessRunState(public=state, seed="DISCOUNT")


@pytest.mark.parametrize(
    ("vouchers", "expected"),
    [
        ((), 0),
        (("v_clearance_sale",), 25),
        (("v_clearance_sale", "v_liquidation"), 50),
        (("v_crystal_ball", "v_clearance_sale"), 25),
        (("v_hone", "v_clearance_sale"), 25),
    ],
)
def test_env_r2_discount_voucher_ownership_implies_exact_percent(vouchers, expected):
    run = _run(vouchers, discount=expected, edition_rate=2.0 if "v_hone" in vouchers else 1.0)

    assert expected_shop_discount_percent_for_vouchers(run.public) == expected
    assert shop_generation_vouchers_are_exact(run.public)
    assert shop_pricing_vouchers_are_exact(run.public)


def test_env_r2_liquidation_without_clearance_fails_closed():
    run = _run(("v_liquidation",), discount=50)

    assert expected_shop_discount_percent_for_vouchers(run.public) is None
    assert not shop_generation_vouchers_are_exact(run.public)
    assert not shop_pricing_vouchers_are_exact(run.public)


def test_env_r2_discount_voucher_state_mismatch_blocks_pricing_not_rng():
    clearance = _run(("v_clearance_sale",), discount=0)
    assert shop_generation_vouchers_are_exact(clearance.public)
    assert not shop_pricing_vouchers_are_exact(clearance.public)

    liquidation = _run(("v_clearance_sale", "v_liquidation"), discount=25)
    assert shop_generation_vouchers_are_exact(liquidation.public)
    assert not shop_pricing_vouchers_are_exact(liquidation.public)

    run = _run(("v_clearance_sale",), discount=25)
    run.public.shop_discount_percent_observed = False
    assert shop_generation_vouchers_are_exact(run.public)
    assert not shop_pricing_vouchers_are_exact(run.public)


def test_env_r2_clearance_prices_tarot_and_planet_from_common_discount_state():
    tarot_run = _run(("v_clearance_sale",), discount=25)
    _, tarot = materialize_base_shop_consumable_descriptor(
        OrdinaryShopConsumableDescriptor(
            run=tarot_run,
            card_type="Tarot",
            center_key="c_fool",
            base_cost=3,
            resamples=0,
        )
    )
    assert tarot.price == 2

    planet_run = _run(("v_clearance_sale",), discount=25)
    _, planet = materialize_base_shop_consumable_descriptor(
        OrdinaryShopConsumableDescriptor(
            run=planet_run,
            card_type="Planet",
            center_key="c_mercury",
            base_cost=3,
            resamples=0,
        )
    )
    assert planet.price == 4


def test_env_r2_liquidation_prices_planet_after_discount_then_multiplier():
    run = _run(("v_clearance_sale", "v_liquidation"), discount=50)

    _, planet = materialize_base_shop_consumable_descriptor(
        OrdinaryShopConsumableDescriptor(
            run=run,
            card_type="Planet",
            center_key="c_mercury",
            base_cost=3,
            resamples=0,
        )
    )

    assert planet.price == 2


def test_env_r2_discount_state_prices_normal_voucher_card_too():
    run = _run(("v_clearance_sale",), discount=25)

    _, item = materialize_normal_shop_voucher_descriptor(
        OrdinaryShopVoucherDescriptor(
            run=run,
            center_key="v_antimatter",
            base_cost=10,
            resamples=0,
        )
    )

    assert item.price == 7


def test_env_r2_consumable_pricing_rejects_owned_discount_mismatch():
    run = _run(("v_clearance_sale",), discount=0)
    descriptor = OrdinaryShopConsumableDescriptor(
        run=run,
        card_type="Tarot",
        center_key="c_fool",
        base_cost=3,
        resamples=0,
    )

    with pytest.raises(HeadlessTransitionError, match="Voucher modifiers"):
        materialize_base_shop_consumable_descriptor(descriptor)
