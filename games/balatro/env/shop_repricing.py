"""Exact immediate repricing for generated visible shop inventory.

Clearance Sale and Liquidation assign ``G.GAME.discount_percent`` and then call
``Card:set_cost`` for existing cards.  This owner is deliberately narrower than
that engine-wide loop: it reprices only headless-generated shop metadata whose
immutable base cost (and Joker edition, when relevant) is still authoritative.
Anything else fails closed instead of reverse-engineering base price from the
currently displayed discounted price.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from games.balatro.env.transition import HeadlessRunState


def reprice_exact_generated_shop(
    run: "HeadlessRunState",
    *,
    discount_percent: int,
) -> "HeadlessRunState":
    """Return an isolated shop snapshot repriced at ``discount_percent``.

    No RNG is consumed.  Booster cards and legacy/live item representations are
    intentionally unsupported because the current headless model cannot prove
    their immutable base cost plus all booster-specific price modifiers.
    """
    # Local imports avoid a transition -> repricing -> shop item -> transition
    # module cycle while keeping the runtime type boundary explicit.
    from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
    from games.balatro.env.shop_items import GeneratedShopJokerItem
    from games.balatro.env.shop_pricing import vanilla_card_cost
    from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
    from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError

    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(discount_percent) is not int or not 0 <= discount_percent <= 100:
        raise HeadlessTransitionError(
            "target shop discount percent must be an exact integer within 0..100"
        )

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("shop repricing requires active SHOP")
    if state.shop_inflation_observed is not True:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if type(state.shop_inflation) is not int or state.shop_inflation < 0:
        raise HeadlessTransitionError(
            "shop inflation must be a nonnegative exact integer"
        )
    if run.tags:
        raise HeadlessTransitionError(
            "shop repricing does not own active Tag price effects"
        )
    if state.shop_boosters:
        raise HeadlessTransitionError(
            "shop repricing does not yet own Booster price modifiers"
        )

    if any(not isinstance(item, GeneratedShopJokerItem) for item in state.shop_jokers):
        raise HeadlessTransitionError(
            "shop repricing requires exact generated Joker metadata"
        )
    if any(
        not isinstance(item, GeneratedShopConsumableItem)
        for item in state.shop_consumables
    ):
        raise HeadlessTransitionError(
            "shop repricing requires exact generated consumable metadata"
        )
    if any(
        not isinstance(item, GeneratedShopVoucherItem)
        for item in state.shop_vouchers
    ):
        raise HeadlessTransitionError(
            "shop repricing requires exact generated Voucher metadata"
        )

    next_run = run.copy()
    next_state = next_run.public

    next_state.shop_jokers = [
        replace(
            item,
            price=vanilla_card_cost(
                item.base_cost,
                edition=item.edition,
                inflation=next_state.shop_inflation,
                discount_percent=discount_percent,
            ),
        )
        for item in next_state.shop_jokers
    ]
    next_state.shop_consumables = [
        replace(
            item,
            price=vanilla_card_cost(
                item.base_cost,
                edition=None,
                inflation=next_state.shop_inflation,
                discount_percent=discount_percent,
                post_discount_multiplier=2 if item.card_type == "Planet" else 1,
            ),
        )
        for item in next_state.shop_consumables
    ]
    next_state.shop_vouchers = [
        replace(
            item,
            price=vanilla_card_cost(
                item.base_cost,
                edition=None,
                inflation=next_state.shop_inflation,
                discount_percent=discount_percent,
            ),
        )
        for item in next_state.shop_vouchers
    ]
    next_state.shop_discount_percent_observed = True
    next_state.shop_discount_percent = discount_percent
    return next_run
