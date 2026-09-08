"""Exact Seed Money / Money Tree Voucher redemption.

Pinned vanilla redemption assigns ``G.GAME.interest_cap`` directly. The purchase
consumes no RNG and changes no already-visible shop item. This owner remains
separate from the training action surface until live interest-cap observation is
wired and validated.
"""

from __future__ import annotations

from typing import Any

from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_INTEREST_CAP_VOUCHER_KEYS,
    interest_cap_vouchers_are_exact,
)

_TARGET_CAPS = {
    "v_seed_money": 50,
    "v_money_tree": 100,
}


def _exact_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if type(value) is not int or value < 0:
        raise HeadlessTransitionError(
            "interest-cap Voucher has no exact nonnegative price"
        )
    return value


def _validated_interest_cap_voucher(
    run: HeadlessRunState,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str, int]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(slot) is not int:
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("interest-cap Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError(
            "interest-cap redemption requires exact generated Voucher metadata"
        )
    key = item.center_key
    if key not in EXACT_INTEREST_CAP_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not in the exact interest-cap family")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")
    if key == "v_money_tree" and "v_seed_money" not in state.vouchers:
        raise HeadlessTransitionError("v_money_tree requires v_seed_money ownership")
    if not interest_cap_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "current Voucher ownership and interest-cap state are not exact"
        )

    price = _exact_price(item)
    if state.money < price:
        raise HeadlessTransitionError("interest-cap Voucher is not affordable")
    return item, key, _TARGET_CAPS[key]


def interest_cap_voucher_redemption_is_exact(
    run: HeadlessRunState,
    slot: int,
) -> bool:
    try:
        _validated_interest_cap_voucher(run, slot)
    except (HeadlessTransitionError, TypeError):
        return False
    return True


def redeem_exact_interest_cap_voucher(
    run: HeadlessRunState,
    slot: int,
) -> HeadlessRunState:
    item, key, target = _validated_interest_cap_voucher(run, slot)
    price = _exact_price(item)

    next_run = run.copy()
    state = next_run.public
    state.money -= price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)
    state.vouchers_observed = True
    state.interest_cap = target
    state.interest_cap_observed = True

    if not interest_cap_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "interest-cap Voucher produced inconsistent post-redemption state"
        )
    return next_run
