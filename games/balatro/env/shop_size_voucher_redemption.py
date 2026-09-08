"""Exact Overstock / Overstock Plus Voucher redemption.

Pinned vanilla redemption queues ``change_shop_size(1)``. That function increments
``G.GAME.shop.joker_max`` and immediately fills every missing main-shop slot via
``create_card_for_shop``. This first exact owner deliberately exposes redemption
only when the pre-redemption main shop is complete, so increasing capacity by one
creates exactly one additional card. Partially depleted-shop replenishment remains
fail closed until separately owned.
"""

from __future__ import annotations

from typing import Any

from games.balatro.env.shop_main_generation import generate_one_base_main_shop_addition
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    EXACT_SHOP_SIZE_VOUCHER_KEYS,
    expected_main_shop_slots_for_vouchers,
)


def _exact_price(item: Any) -> int:
    value = getattr(item, "price", None)
    if type(value) is not int or value < 0:
        raise HeadlessTransitionError(
            "shop-size Voucher has no exact nonnegative price"
        )
    return value


def _apply_purchase_without_generation(
    run: HeadlessRunState,
    slot: int,
    key: str,
    price: int,
) -> HeadlessRunState:
    next_run = run.copy()
    state = next_run.public
    state.money -= price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)
    state.vouchers_observed = True
    return next_run


def _validated_shop_size_voucher(
    run: HeadlessRunState,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str, int, int]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(slot) is not int:
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("shop-size Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError(
            "shop-size redemption requires exact generated Voucher metadata"
        )
    key = item.center_key
    if key not in EXACT_SHOP_SIZE_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not in the exact shop-size family")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")
    if key == "v_overstock_plus" and "v_overstock_norm" not in state.vouchers:
        raise HeadlessTransitionError(
            "v_overstock_plus requires v_overstock_norm ownership"
        )

    current_slots = expected_main_shop_slots_for_vouchers(state)
    if current_slots is None:
        raise HeadlessTransitionError("current main-shop capacity is not exact")
    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied != current_slots:
        raise HeadlessTransitionError(
            "shop-size Voucher currently requires a complete pre-redemption main shop"
        )

    price = _exact_price(item)
    if state.money < price:
        raise HeadlessTransitionError("shop-size Voucher is not affordable")

    # Prove the entire post-redemption side effect before exposing legality.
    # This advances RNG only on an isolated copy and therefore has no side effect
    # on the caller if catalogue/pricing/tag state makes replenishment inexact.
    preview = _apply_purchase_without_generation(run, slot, key, price)
    target_slots = expected_main_shop_slots_for_vouchers(preview.public)
    if target_slots != current_slots + 1:
        raise HeadlessTransitionError("shop-size Voucher progression is inconsistent")
    preview_result = generate_one_base_main_shop_addition(preview)
    preview_occupied = (
        len(preview_result.run.public.shop_jokers)
        + len(preview_result.run.public.shop_consumables)
    )
    if preview_occupied != target_slots:
        raise HeadlessTransitionError(
            "shop-size Voucher preview did not fill the new main-shop slot"
        )

    return item, key, price, target_slots


def shop_size_voucher_redemption_is_exact(
    run: HeadlessRunState,
    slot: int,
) -> bool:
    try:
        _validated_shop_size_voucher(run, slot)
    except (HeadlessTransitionError, TypeError, ValueError):
        return False
    return True


def redeem_exact_shop_size_voucher(
    run: HeadlessRunState,
    slot: int,
) -> HeadlessRunState:
    _, key, price, target_slots = _validated_shop_size_voucher(run, slot)

    purchased = _apply_purchase_without_generation(run, slot, key, price)
    result = generate_one_base_main_shop_addition(purchased).run
    occupied = len(result.public.shop_jokers) + len(result.public.shop_consumables)
    if occupied != target_slots:
        raise HeadlessTransitionError(
            "shop-size Voucher produced inconsistent post-redemption capacity"
        )
    return result
