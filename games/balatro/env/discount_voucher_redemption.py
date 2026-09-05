"""Exact Clearance Sale / Liquidation redemption transaction.

Vanilla pays the Voucher at its current price, records the Voucher as used, assigns
``G.GAME.discount_percent``, then calls ``Card:set_cost`` over visible cards.  This
owner mirrors that ordering for the subset of visible shop metadata whose immutable
base costs are already authoritative.  Unsupported Booster/legacy inventory stays
fail-closed through :func:`reprice_exact_generated_shop`.
"""

from __future__ import annotations

from typing import Any

from games.balatro.env.shop_repricing import reprice_exact_generated_shop
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_DISCOUNT_VOUCHER_KEYS,
    shop_pricing_vouchers_are_exact,
)


_TARGET_DISCOUNT_PERCENT = {
    "v_clearance_sale": 25,
    "v_liquidation": 50,
}


def _exact_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if type(value) is not int or value < 0:
        raise HeadlessTransitionError("discount Voucher has no exact nonnegative price")
    return value


def _validated_discount_voucher(
    run: HeadlessRunState,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str, int]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(slot) is not int:
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("discount Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError(
            "discount Voucher redemption requires exact generated Voucher metadata"
        )
    key = item.center_key
    if key not in EXACT_DISCOUNT_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not in the exact discount family")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")
    if key == "v_liquidation" and "v_clearance_sale" not in state.vouchers:
        raise HeadlessTransitionError("Liquidation requires Clearance Sale ownership")
    if not shop_pricing_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "current Voucher ownership and shop discount state are not exact"
        )

    price = _exact_price(item)
    if state.money < price:
        raise HeadlessTransitionError("discount Voucher is not affordable")

    target = _TARGET_DISCOUNT_PERCENT[key]
    # Preflight the complete currently visible shop before exposing this action.
    # The result is intentionally discarded: vanilla pays the Voucher at the old
    # price and reprices only after ownership changes.
    reprice_exact_generated_shop(run, discount_percent=target)
    return item, key, target


def discount_voucher_redemption_is_exact(
    run: HeadlessRunState,
    slot: int,
) -> bool:
    """Return whether one discount Voucher purchase is exact and executable."""
    try:
        _validated_discount_voucher(run, slot)
    except (HeadlessTransitionError, TypeError):
        return False
    return True


def redeem_exact_discount_voucher(
    run: HeadlessRunState,
    slot: int,
) -> HeadlessRunState:
    """Pay, record, and atomically reprice one exact discount Voucher purchase."""
    item, key, target = _validated_discount_voucher(run, slot)
    old_price = _exact_price(item)

    next_run = run.copy()
    state = next_run.public
    state.money -= old_price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)

    # Reprice only the remaining visible shop after the purchased Voucher leaves
    # its area.  This consumes no RNG and also installs authoritative discount
    # state matching the newly recorded ownership.
    return reprice_exact_generated_shop(next_run, discount_percent=target)
