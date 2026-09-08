from types import SimpleNamespace

import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.state import BalatroState


_RESOURCE_CASES = (
    ("v_crystal_ball", "consumable_slots", 2, 3),
    ("v_grabber", "round_reset_hands", 4, 5),
    ("v_nacho_tong", "round_reset_hands", 4, 5),
    ("v_wasteful", "round_reset_discards", 4, 5),
    ("v_recyclomancy", "round_reset_discards", 4, 5),
    ("v_antimatter", "joker_slots", 5, 6),
    ("v_paint_brush", "hand_size", 8, 9),
    ("v_palette", "hand_size", 8, 9),
)


def _run(center_key: str = "v_crystal_ball", *, price=10) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.hands_remaining = 2
    state.discards_remaining = 1
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 4
    state.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key=center_key,
            base_cost=10,
            price=price,
        )
    ]
    return HeadlessRunState(public=state, seed="VOUCHER-RESOURCE")


def _buy(slot: int = 0) -> EnvAction:
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": slot})


@pytest.mark.parametrize("center_key,field,before,after", _RESOURCE_CASES)
def test_env_r2_resource_voucher_is_legal_and_redeems_exactly(
    center_key,
    field,
    before,
    after,
):
    engine = ShopTransitionEngine()
    run = _run(center_key)
    source_money = run.public.money
    source_voucher = run.public.shop_vouchers[0]

    assert getattr(run.public, field) == before
    assert _buy() in engine.legal_actions(run)

    result = engine.step(run, _buy())

    assert result is not run
    assert result.public.money == source_money - 10
    assert result.public.shop_vouchers == []
    assert result.public.vouchers == [center_key]
    assert getattr(result.public, field) == after

    # Deep-copy transition isolation: neither the source slot nor source resources
    # may be modified by a successful redemption.
    assert run.public.money == source_money
    assert run.public.shop_vouchers == [source_voucher]
    assert run.public.vouchers == []
    assert getattr(run.public, field) == before


@pytest.mark.parametrize("center_key", ("v_grabber", "v_nacho_tong"))
def test_env_r2_hand_allowance_vouchers_update_current_and_reset_hands(center_key):
    result = ShopTransitionEngine().step(_run(center_key), _buy())

    assert result.public.round_reset_hands == 5
    assert result.public.hands_remaining == 3


@pytest.mark.parametrize("center_key", ("v_wasteful", "v_recyclomancy"))
def test_env_r2_discard_allowance_vouchers_update_current_and_reset_discards(center_key):
    result = ShopTransitionEngine().step(_run(center_key), _buy())

    assert result.public.round_reset_discards == 5
    assert result.public.discards_remaining == 2


@pytest.mark.parametrize("center_key", ("v_grabber", "v_nacho_tong"))
def test_env_r2_hand_allowance_vouchers_fail_closed_without_reset_observation(center_key):
    engine = ShopTransitionEngine()
    run = _run(center_key)
    run.public.round_reset_hands_observed = False
    before = run.public.copy()

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())

    assert run.public.money == before.money
    assert run.public.shop_vouchers == before.shop_vouchers
    assert run.public.vouchers == before.vouchers


@pytest.mark.parametrize("center_key", ("v_wasteful", "v_recyclomancy"))
def test_env_r2_discard_allowance_vouchers_fail_closed_without_reset_observation(center_key):
    engine = ShopTransitionEngine()
    run = _run(center_key)
    run.public.round_reset_discards_observed = False
    before = run.public.copy()

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())

    assert run.public.money == before.money
    assert run.public.shop_vouchers == before.shop_vouchers
    assert run.public.vouchers == before.vouchers


def test_env_r2_unsupported_voucher_remains_absent_and_direct_execution_rejects():
    engine = ShopTransitionEngine()
    run = _run("v_overstock_norm")

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())

    assert run.public.money == 20
    assert len(run.public.shop_vouchers) == 1
    assert run.public.vouchers == []


def test_env_r2_duplicate_owned_voucher_is_not_redeemable():
    engine = ShopTransitionEngine()
    run = _run("v_crystal_ball")
    run.public.vouchers = ["v_crystal_ball"]

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())


def test_env_r2_malformed_voucher_key_and_price_fail_closed():
    engine = ShopTransitionEngine()

    missing_key = _run()
    missing_key.public.shop_vouchers = [SimpleNamespace(price=10)]
    assert _buy() not in engine.legal_actions(missing_key)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(missing_key, _buy())

    bad_price = _run()
    bad_price.public.shop_vouchers = [
        SimpleNamespace(center_key="v_crystal_ball", price=10.0)
    ]
    assert _buy() not in engine.legal_actions(bad_price)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(bad_price, _buy())


def test_env_r2_unaffordable_resource_voucher_is_not_legal():
    engine = ShopTransitionEngine()
    run = _run("v_antimatter", price=21)

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())


def test_env_r2_voucher_slot_must_exist():
    engine = ShopTransitionEngine()
    run = _run("v_antimatter")

    assert _buy(1) not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy(1))
