"""Exact Tarot/Planet Merchant/Tycoon Voucher redemption.

Pinned vanilla redemption assigns ``G.GAME.tarot_rate`` or
``G.GAME.planet_rate`` directly. It does not reroll, replace, or reprice any
currently visible shop card and consumes no RNG. This owner therefore changes
only money, Voucher ownership, and the corresponding persistent future type
weight after proving the pre-purchase ownership/rate state is exact.
"""

from __future__ import annotations

from typing import Any

from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS,
    shop_generation_vouchers_are_exact,
)


_TARGET_RATES = {
    "v_tarot_merchant": ("tarot_rate", 9.6),
    "v_tarot_tycoon": ("tarot_rate", 32.0),
    "v_planet_merchant": ("planet_rate", 9.6),
    "v_planet_tycoon": ("planet_rate", 32.0),
}

_UPGRADE_REQUIREMENTS = {
    "v_tarot_tycoon": "v_tarot_merchant",
    "v_planet_tycoon": "v_planet_merchant",
}


def _exact_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if type(value) is not int or value < 0:
        raise HeadlessTransitionError(
            "shop type-rate Voucher has no exact nonnegative price"
        )
    return value


def _validated_type_rate_voucher(
    run: HeadlessRunState,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str, str, float]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(slot) is not int:
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("shop type-rate Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError(
            "shop type-rate redemption requires exact generated Voucher metadata"
        )
    key = item.center_key
    if key not in EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not in the exact shop type-rate family")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")

    required = _UPGRADE_REQUIREMENTS.get(key)
    if required is not None and required not in state.vouchers:
        raise HeadlessTransitionError(f"{key} requires {required} ownership")

    # Never repair a stale or partially observed modifier state by buying the
    # next Voucher. Exact current shop generation must already agree with all
    # observed Voucher ownership before this transition becomes legal.
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "current Voucher ownership and shop type-rate state are not exact"
        )

    price = _exact_price(item)
    if state.money < price:
        raise HeadlessTransitionError("shop type-rate Voucher is not affordable")

    field, target = _TARGET_RATES[key]
    return item, key, field, target


def shop_type_rate_voucher_redemption_is_exact(
    run: HeadlessRunState,
    slot: int,
) -> bool:
    """Return whether one Merchant/Tycoon purchase is exact and executable."""
    try:
        _validated_type_rate_voucher(run, slot)
    except (HeadlessTransitionError, TypeError):
        return False
    return True


def redeem_exact_shop_type_rate_voucher(
    run: HeadlessRunState,
    slot: int,
) -> HeadlessRunState:
    """Pay and install one exact future normal-shop type-rate modifier."""
    item, key, field, target = _validated_type_rate_voucher(run, slot)
    price = _exact_price(item)

    next_run = run.copy()
    state = next_run.public
    state.money -= price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)
    state.vouchers_observed = True
    setattr(state, field, target)

    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "shop type-rate Voucher produced inconsistent post-redemption state"
        )
    return next_run
