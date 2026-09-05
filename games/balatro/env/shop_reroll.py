"""Exact R2 normal paid shop-reroll lifecycle.

Pinned vanilla order for ``G.FUNCS.reroll_shop`` is:

1. charge the current positive reroll cost;
2. consume free-reroll state / increment reroll counters;
3. ``calculate_reroll_cost(final_free)``;
4. remove every card in the shared main-shop area;
5. regenerate missing slots through ``create_card_for_shop``.

The owned boundary covers ordinary paid rerolls with exact Voucher-derived base
reroll cost and main-shop capacity. Bankruptcy, free-reroll and Tag temporary
modifiers remain blocked. Inventory RNG is delegated to ``generate_base_main_shop``.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_main_generation import GeneratedMainShop, generate_base_main_shop
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    expected_base_reroll_cost_for_vouchers,
    expected_main_shop_slots_for_vouchers,
    shop_generation_vouchers_are_exact,
)
from games.balatro.jokers.chaos_the_clown import ChaosTheClownJoker
from games.balatro.jokers.credit_card import CreditCardJoker


@dataclass(frozen=True)
class PaidBaseShopReroll:
    run: HeadlessRunState
    previous_cost: int
    next_cost: int
    items: tuple[GeneratedShopJokerItem | GeneratedShopConsumableItem, ...]


def validate_paid_base_reroll(run: HeadlessRunState) -> None:
    """Validate the exact ordinary paid-reroll boundary.

    This is the single mechanics owner used by both legality/masking code and
    ``reroll_base_main_shop``.  Callers must not duplicate these conditions.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("paid reroll requires active SHOP")
    if not shop_generation_vouchers_are_exact(state):
        raise HeadlessTransitionError("paid reroll does not own current Voucher modifiers")
    if run.tags:
        raise HeadlessTransitionError("paid reroll does not own active Tag modifiers")
    if any(isinstance(joker, CreditCardJoker) for joker in state.jokers):
        raise HeadlessTransitionError("paid reroll does not own bankruptcy allowance")
    if any(isinstance(joker, ChaosTheClownJoker) for joker in state.jokers):
        raise HeadlessTransitionError("paid reroll does not own free-reroll state")

    expected_base = expected_base_reroll_cost_for_vouchers(state)
    if expected_base is None or run.base_reroll_cost != expected_base:
        raise HeadlessTransitionError(
            "persistent reroll cost does not match current Voucher ownership"
        )
    if type(run.reroll_cost) is not int or run.reroll_cost < run.base_reroll_cost:
        raise HeadlessTransitionError(
            "paid reroll requires an exact current cost without temporary/free modifiers"
        )
    if type(state.money) is not int:
        raise HeadlessTransitionError("paid reroll requires exact integer money")
    if state.money < run.reroll_cost:
        raise HeadlessTransitionError("cannot afford paid shop reroll")

    expected_slots = expected_main_shop_slots_for_vouchers(state)
    if expected_slots is None:
        raise HeadlessTransitionError("paid reroll main-shop capacity is not exact")
    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied != expected_slots:
        raise HeadlessTransitionError(
            "paid reroll requires a complete current-capacity main shop"
        )

    # Vanilla reroll only replaces cards in G.shop_jokers, the shared main-shop
    # area. Booster and Voucher areas are independent and remain untouched, so
    # their presence is not a reason to reject an otherwise exact reroll.


def can_reroll_base_main_shop(run: HeadlessRunState) -> bool:
    """Return whether the exact ordinary paid-reroll transition is available."""
    try:
        validate_paid_base_reroll(run)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def reroll_base_main_shop(run: HeadlessRunState) -> PaidBaseShopReroll:
    """Perform one exact ordinary paid reroll and regenerate all main slots."""
    validate_paid_base_reroll(run)

    previous_cost = run.reroll_cost
    next_run = run.copy()

    # Vanilla queues the dollar deduction before the immediate reroll event.
    next_run.public.money -= previous_cost

    # With no free-reroll/temp modifiers, calculate_reroll_cost(false) increments
    # reroll_cost_increase by one. Persistent Voucher reductions are already
    # represented in base_reroll_cost, so current + 1 remains exact.
    next_run.reroll_cost = previous_cost + 1

    # G.shop_jokers is the shared physical main-shop area. Canonical state splits
    # that area by item category, so both category lists must be cleared together.
    next_run.public.shop_jokers = []
    next_run.public.shop_consumables = []

    generated: GeneratedMainShop = generate_base_main_shop(next_run)
    return PaidBaseShopReroll(
        run=generated.run,
        previous_cost=previous_cost,
        next_cost=generated.run.reroll_cost,
        items=generated.items,
    )