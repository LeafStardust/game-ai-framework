"""Exact first R2 slice of the normal paid shop-reroll lifecycle.

Pinned vanilla order for ``G.FUNCS.reroll_shop`` is:

1. charge the current positive reroll cost;
2. consume free-reroll state / increment reroll counters;
3. ``calculate_reroll_cost(final_free)``;
4. remove every card in the shared main-shop area;
5. regenerate missing slots through ``create_card_for_shop``.

This first headless boundary owns only ordinary *paid* rerolls with no bankruptcy,
free-reroll, voucher, or Tag modifiers. It reuses ``generate_base_main_shop`` for
all inventory RNG and never duplicates shop-generation mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_main_generation import GeneratedMainShop, generate_base_main_shop
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.chaos_the_clown import ChaosTheClownJoker
from games.balatro.jokers.credit_card import CreditCardJoker


_BASE_REROLL_COST = 5
_BASE_MAIN_SHOP_SLOTS = 2


@dataclass(frozen=True)
class PaidBaseShopReroll:
    run: HeadlessRunState
    previous_cost: int
    next_cost: int
    items: tuple[GeneratedShopJokerItem | GeneratedShopConsumableItem, ...]


def _validate_paid_base_reroll(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("paid reroll requires active SHOP")
    if state.vouchers:
        raise HeadlessTransitionError("base paid reroll does not own voucher modifiers")
    if run.tags:
        raise HeadlessTransitionError("base paid reroll does not own active Tag modifiers")
    if any(isinstance(joker, CreditCardJoker) for joker in state.jokers):
        raise HeadlessTransitionError("base paid reroll does not own bankruptcy allowance")
    if any(isinstance(joker, ChaosTheClownJoker) for joker in state.jokers):
        raise HeadlessTransitionError("base paid reroll does not own free-reroll state")

    if type(run.reroll_cost) is not int or run.reroll_cost < _BASE_REROLL_COST:
        raise HeadlessTransitionError(
            "base paid reroll requires an exact positive unmodified reroll cost"
        )
    if type(state.money) is not int:
        raise HeadlessTransitionError("paid reroll requires exact integer money")
    if state.money < run.reroll_cost:
        raise HeadlessTransitionError("cannot afford paid shop reroll")

    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied != _BASE_MAIN_SHOP_SLOTS:
        raise HeadlessTransitionError("paid reroll requires a complete two-card main shop")
    if state.shop_boosters or state.shop_vouchers:
        raise HeadlessTransitionError(
            "base paid reroll boundary does not yet compose booster/voucher shop areas"
        )


def reroll_base_main_shop(run: HeadlessRunState) -> PaidBaseShopReroll:
    """Perform one exact ordinary paid reroll and regenerate the two main slots."""
    _validate_paid_base_reroll(run)

    previous_cost = run.reroll_cost
    next_run = run.copy()

    # Vanilla queues the dollar deduction before the immediate reroll event.
    next_run.public.money -= previous_cost

    # With no free-reroll/temp/voucher modifiers, calculate_reroll_cost(false)
    # increments reroll_cost_increase by one, exactly equivalent to current + 1.
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
