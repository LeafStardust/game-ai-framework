"""Exact pricing for the currently owned normal unmodified shop boundary.

Vanilla ``Card:set_cost`` computes a card's purchase price from immutable center
base cost, run inflation, edition surcharge, and discount percentage. The current
Red Deck / White Stake normal-mode base-shop generator explicitly rejects voucher
and active-Tag modifiers and does not model challenge inflation, so the owned
boundary is exactly ``inflation=0`` and ``discount_percent=0``.

Do not widen this function by silently accepting modifier state; add canonical
state ownership first.
"""

from __future__ import annotations

import math

from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.transition import HeadlessTransitionError


_EDITION_SURCHARGE: dict[str | None, int] = {
    None: 0,
    "Foil": 2,
    "Holographic": 3,
    "Polychrome": 5,
    "Negative": 5,
}


def vanilla_card_cost(
    base_cost: int,
    *,
    edition: str | None,
    inflation: int,
    discount_percent: int,
) -> int:
    """Return vanilla ``Card:set_cost`` purchase cost for exact integer inputs."""
    for name, value in (
        ("base_cost", base_cost),
        ("inflation", inflation),
        ("discount_percent", discount_percent),
    ):
        if type(value) is not int:
            raise HeadlessTransitionError(f"{name} must be an exact integer")
    if base_cost < 0:
        raise HeadlessTransitionError("base_cost cannot be negative")
    if inflation < 0:
        raise HeadlessTransitionError("inflation cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise HeadlessTransitionError("discount_percent must be within 0..100")
    if edition not in _EDITION_SURCHARGE:
        raise HeadlessTransitionError("unsupported Joker edition for exact pricing")

    extra_cost = inflation + _EDITION_SURCHARGE[edition]
    return max(
        1,
        math.floor((base_cost + extra_cost + 0.5) * (100 - discount_percent) / 100),
    )


def price_base_shop_joker_descriptor(descriptor: OrdinaryShopJokerDescriptor) -> int:
    """Price one descriptor inside the frozen normal unmodified shop boundary."""
    if not isinstance(descriptor, OrdinaryShopJokerDescriptor):
        raise TypeError("descriptor must be OrdinaryShopJokerDescriptor")
    run = descriptor.run
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("base Joker pricing requires an active SHOP")
    if state.vouchers:
        raise HeadlessTransitionError("base Joker pricing does not own voucher discounts")
    if run.tags:
        raise HeadlessTransitionError("base Joker pricing does not own active Tag price effects")

    return vanilla_card_cost(
        descriptor.base_cost,
        edition=descriptor.edition,
        inflation=0,
        discount_percent=0,
    )
