"""Exact Balatro ``Card:set_cost`` pricing for generated shop cards.

Vanilla pricing consumes immutable center base cost plus ordinary ``G.GAME``
``inflation`` and ``discount_percent`` state.  Planet consumables then apply their
vanilla post-discount x2 shop-cost rule.  These mechanics-critical values must be
canonical and authoritative before generated metadata is priced.

Active Tag effects remain a separate materialization boundary and therefore stay
fail-closed until their price/creation consequences are audited end-to-end.
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
    post_discount_multiplier: int = 1,
) -> int:
    """Return vanilla ``Card:set_cost`` purchase cost for exact integer inputs.

    ``post_discount_multiplier`` owns effects that vanilla applies only after the
    ordinary rounded/discounted card cost.  Ordinary cards use ``1``; Planet
    consumables use ``2``.  Keeping this operation explicit prevents an
    equivalent-looking but incorrect ``(base * 2) then discount`` shortcut.
    """
    for name, value in (
        ("base_cost", base_cost),
        ("inflation", inflation),
        ("discount_percent", discount_percent),
        ("post_discount_multiplier", post_discount_multiplier),
    ):
        if type(value) is not int:
            raise HeadlessTransitionError(f"{name} must be an exact integer")
    if base_cost < 0:
        raise HeadlessTransitionError("base_cost cannot be negative")
    if inflation < 0:
        raise HeadlessTransitionError("inflation cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise HeadlessTransitionError("discount_percent must be within 0..100")
    if post_discount_multiplier < 1:
        raise HeadlessTransitionError("post_discount_multiplier must be positive")
    if edition not in _EDITION_SURCHARGE:
        raise HeadlessTransitionError("unsupported Joker edition for exact pricing")

    extra_cost = inflation + _EDITION_SURCHARGE[edition]
    ordinary_cost = max(
        1,
        math.floor((base_cost + extra_cost + 0.5) * (100 - discount_percent) / 100),
    )
    return ordinary_cost * post_discount_multiplier


def price_base_shop_joker_descriptor(descriptor: OrdinaryShopJokerDescriptor) -> int:
    """Price one descriptor from authoritative canonical pricing state."""
    if not isinstance(descriptor, OrdinaryShopJokerDescriptor):
        raise TypeError("descriptor must be OrdinaryShopJokerDescriptor")
    run = descriptor.run
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("base Joker pricing requires an active SHOP")
    if not isinstance(state.shop_inflation_observed, bool):
        raise HeadlessTransitionError("shop_inflation_observed must be a boolean")
    if not state.shop_inflation_observed:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if not isinstance(state.shop_discount_percent_observed, bool):
        raise HeadlessTransitionError("shop_discount_percent_observed must be a boolean")
    if not state.shop_discount_percent_observed:
        raise HeadlessTransitionError("shop discount percent is not authoritative")
    if run.tags:
        raise HeadlessTransitionError("base Joker pricing does not own active Tag price effects")

    return vanilla_card_cost(
        descriptor.base_cost,
        edition=descriptor.edition,
        inflation=state.shop_inflation,
        discount_percent=state.shop_discount_percent,
    )
