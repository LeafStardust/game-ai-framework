import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
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
    return HeadlessRunState(public=state, seed="DISCOUNT-ENGINE")


def _install(run, voucher):
    run.public.shop_jokers = [
        GeneratedShopJokerItem(
            center_key="j_joker",
            rarity=1,
            base_cost=5,
            edition=None,
            price=5 if run.public.shop_discount_percent == 0 else 4,
        )
    ]
    run.public.shop_consumables = [
        GeneratedShopConsumableItem(
            card_type="Tarot",
            center_key="c_fool",
            base_cost=3,
            price=3 if run.public.shop_discount_percent == 0 else 2,
        )
    ]
    run.public.shop_vouchers = [voucher]
    return run


def _buy_voucher():
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": 0})


def test_env_r2_shop_engine_exposes_and_executes_clearance_transaction():
    run = _install(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        ),
    )
    engine = ShopTransitionEngine()
    action = _buy_voucher()
    before_rng = run.rng_snapshot()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert result.public.money == 20
    assert result.public.vouchers == ["v_clearance_sale"]
    assert result.public.shop_vouchers == []
    assert result.public.shop_discount_percent == 25
    assert result.public.shop_jokers[0].price == 4
    assert result.public.shop_consumables[0].price == 2
    assert result.rng_snapshot() == before_rng
    assert run.public.money == 30
    assert run.public.vouchers == []
    assert run.public.shop_discount_percent == 0


def test_env_r2_shop_engine_exposes_liquidation_only_after_exact_clearance_state():
    engine = ShopTransitionEngine()
    action = _buy_voucher()

    impossible = _install(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=10,
        ),
    )
    assert action not in engine.legal_actions(impossible)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(impossible, action)

    run = _install(
        _run(vouchers=("v_clearance_sale",), discount=25),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=7,
        ),
    )
    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert result.public.money == 23
    assert result.public.vouchers == ["v_clearance_sale", "v_liquidation"]
    assert result.public.shop_discount_percent == 50
    assert result.public.shop_jokers[0].price == 2
    assert result.public.shop_consumables[0].price == 1


def test_env_r2_shop_engine_hides_discount_purchase_when_repricing_is_not_owned():
    engine = ShopTransitionEngine()
    action = _buy_voucher()

    booster_run = _install(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        ),
    )
    booster_run.public.shop_boosters = [object()]
    assert action not in engine.legal_actions(booster_run)

    legacy_run = _run()
    legacy_run.public.shop_jokers = [object()]
    legacy_run.public.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        )
    ]
    assert action not in engine.legal_actions(legacy_run)

    mismatch_run = _install(
        _run(vouchers=("v_clearance_sale",), discount=0),
        GeneratedShopVoucherItem(
            center_key="v_liquidation",
            base_cost=10,
            price=10,
        ),
    )
    assert action not in engine.legal_actions(mismatch_run)


def test_env_r2_shop_engine_hides_discount_purchase_when_current_generated_price_is_stale():
    run = _install(
        _run(),
        GeneratedShopVoucherItem(
            center_key="v_clearance_sale",
            base_cost=10,
            price=10,
        ),
    )
    run.public.shop_jokers[0] = GeneratedShopJokerItem(
        center_key="j_joker",
        rarity=1,
        base_cost=5,
        edition=None,
        price=4,
    )

    assert _buy_voucher() not in ShopTransitionEngine().legal_actions(run)
