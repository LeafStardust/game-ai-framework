import pytest

from games.balatro.env.discount_voucher_redemption import (
    discount_voucher_redemption_is_exact,
    redeem_exact_discount_voucher,
)
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(*, vouchers=(), discount=0, money=30):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = money
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.joker_generation_edition_rate = 1.0
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = discount
    return HeadlessRunState(public=state, seed="DISCOUNT-REDEEM")


def _install_visible_inventory(run, voucher):
    run.public.shop_jokers = [
        GeneratedShopJokerItem(
            center_key="j_joker",
            rarity=1,
            base_cost=5,
            edition="Foil",
            price=7 if run.public.shop_discount_percent == 0 else 5,
        )
    ]
    run.public.shop_consumables = [
        GeneratedShopConsumableItem(
            card_type="Planet",
            center_key="c_mercury",
            base_cost=3,
            price=6 if run.public.shop_discount_percent == 0 else 4,
        )
    ]
    run.public.shop_vouchers = [voucher]
    return run


def test_env_r2_clearance_redemption_pays_old_price_then_reprices_remaining_shop():
    run = _install_visible_inventory(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        ),
    )
    before_rng = run.rng_snapshot()

    assert discount_voucher_redemption_is_exact(run, 0)
    result = redeem_exact_discount_voucher(run, 0)

    assert result.public.money == 20
    assert result.public.vouchers == ["v_clearance_sale"]
    assert result.public.shop_vouchers == []
    assert result.public.shop_discount_percent_observed is True
    assert result.public.shop_discount_percent == 25
    assert result.public.shop_jokers[0].price == 5
    assert result.public.shop_consumables[0].price == 4
    assert result.rng_snapshot() == before_rng

    # Input isolation: neither economy nor visible metadata may be mutated in place.
    assert run.public.money == 30
    assert run.public.vouchers == []
    assert run.public.shop_discount_percent == 0
    assert run.public.shop_jokers[0].price == 7
    assert run.public.shop_consumables[0].price == 6
    assert run.public.shop_vouchers[0].price == 10
    assert run.rng_snapshot() == before_rng


def test_env_r2_liquidation_requires_clearance_then_reprices_25_to_50_percent():
    impossible = _install_visible_inventory(
        _run(discount=0),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=10,
        ),
    )
    assert not discount_voucher_redemption_is_exact(impossible, 0)
    with pytest.raises(HeadlessTransitionError, match="requires Clearance"):
        redeem_exact_discount_voucher(impossible, 0)

    run = _install_visible_inventory(
        _run(vouchers=("v_clearance_sale",), discount=25),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=7,
        ),
    )
    before_rng = run.rng_snapshot()

    result = redeem_exact_discount_voucher(run, 0)

    assert result.public.money == 23
    assert result.public.vouchers == ["v_clearance_sale", "v_liquidation"]
    assert result.public.shop_discount_percent == 50
    assert result.public.shop_jokers[0].price == 3
    assert result.public.shop_consumables[0].price == 2
    assert result.rng_snapshot() == before_rng


def test_env_r2_discount_redemption_preflight_rejects_boosters_without_mutation():
    run = _install_visible_inventory(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        ),
    )
    run.public.shop_boosters = [object()]
    before_rng = run.rng_snapshot()

    assert not discount_voucher_redemption_is_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="Booster price modifiers"):
        redeem_exact_discount_voucher(run, 0)

    assert run.public.money == 30
    assert run.public.vouchers == []
    assert run.public.shop_discount_percent == 0
    assert run.rng_snapshot() == before_rng


def test_env_r2_discount_redemption_preflight_rejects_legacy_visible_inventory():
    run = _run()
    run.public.shop_jokers = [object()]
    run.public.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        )
    ]

    assert not discount_voucher_redemption_is_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="generated Joker metadata"):
        redeem_exact_discount_voucher(run, 0)


def test_env_r2_discount_redemption_rejects_current_ownership_percent_mismatch():
    run = _install_visible_inventory(
        _run(vouchers=("v_clearance_sale",), discount=0),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=10,
        ),
    )

    assert not discount_voucher_redemption_is_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="discount state are not exact"):
        redeem_exact_discount_voucher(run, 0)


def test_env_r2_discount_redemption_rejects_unaffordable_and_non_discount_voucher():
    unaffordable = _run(money=9)
    unaffordable.public.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        )
    ]
    assert not discount_voucher_redemption_is_exact(unaffordable, 0)

    other = _run()
    other.public.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key="v_hone",
            base_cost=10,
            price=10,
        )
    ]
    assert not discount_voucher_redemption_is_exact(other, 0)
    with pytest.raises(HeadlessTransitionError, match="exact discount family"):
        redeem_exact_discount_voucher(other, 0)
