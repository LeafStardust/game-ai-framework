"""Exact Reroll Surplus / Reroll Glut Voucher redemption.

Pinned vanilla changes two values when either Voucher is redeemed:

* persistent ``G.GAME.round_resets.reroll_cost -= 2``;
* current ``G.GAME.current_round.reroll_cost = max(0, current - 2)``.

The headless environment mirrors those as ``HeadlessRunState.base_reroll_cost``
and ``HeadlessRunState.reroll_cost``. Redemption consumes no RNG and does not
replace currently visible shop inventory.
"""

from __future__ import annotations

from typing import Any

from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_REROLL_COST_VOUCHER_KEYS,
    expected_base_reroll_cost_for_vouchers,
    shop_generation_vouchers_are_exact,
)


_UPGRADE_REQUIREMENTS = {
    "v_reroll_glut": "v_reroll_surplus",
}


def _exact_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if type(value) is not int or value < 0:
        raise HeadlessTransitionError(
            "reroll Voucher has no exact nonnegative price"
        )
    return value


def _validated_reroll_voucher(
    run: HeadlessRunState,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(slot) is not int:
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("reroll Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError(
            "reroll Voucher redemption requires exact generated Voucher metadata"
        )
    key = item.center_key
    if key not in EXACT_REROLL_COST_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not in the exact reroll-cost family")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")

    required = _UPGRADE_REQUIREMENTS.get(key)
    if required is not None and required not in state.vouchers:
        raise HeadlessTransitionError(f"{key} requires {required} ownership")

    # Existing exact Voucher ownership must already agree with every currently
    # owned shop-generation modifier before we widen that ownership set.
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "current Voucher ownership and shop-generation state are not exact"
        )

    expected_base = expected_base_reroll_cost_for_vouchers(state)
    if expected_base is None or run.base_reroll_cost != expected_base:
        raise HeadlessTransitionError(
            "persistent reroll cost does not match current Voucher ownership"
        )
    if type(run.reroll_cost) is not int or run.reroll_cost < run.base_reroll_cost:
        raise HeadlessTransitionError(
            "current reroll cost contains an unowned temporary/free modifier"
        )

    price = _exact_price(item)
    if state.money < price:
        raise HeadlessTransitionError("reroll Voucher is not affordable")

    return item, key


def reroll_voucher_redemption_is_exact(run: HeadlessRunState, slot: int) -> bool:
    """Return whether one Surplus/Glut redemption is exact and executable."""
    try:
        _validated_reroll_voucher(run, slot)
    except (HeadlessTransitionError, TypeError):
        return False
    return True


def redeem_exact_reroll_voucher(
    run: HeadlessRunState,
    slot: int,
) -> HeadlessRunState:
    """Pay for and install one exact persistent/current reroll-cost reduction."""
    item, key = _validated_reroll_voucher(run, slot)
    price = _exact_price(item)

    next_run = run.copy()
    state = next_run.public
    state.money -= price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)
    state.vouchers_observed = True

    next_run.base_reroll_cost -= 2
    next_run.reroll_cost = max(0, next_run.reroll_cost - 2)

    expected_base = expected_base_reroll_cost_for_vouchers(state)
    if expected_base is None or next_run.base_reroll_cost != expected_base:
        raise HeadlessTransitionError(
            "reroll Voucher produced inconsistent persistent reroll state"
        )
    if next_run.reroll_cost < next_run.base_reroll_cost:
        raise HeadlessTransitionError(
            "reroll Voucher produced inconsistent current reroll state"
        )
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError(
            "reroll Voucher produced inconsistent shop-generation state"
        )

    return next_run
