"""Exact normal-shop Voucher metadata, pricing and slot publication.

Pinned vanilla keeps the ordinary round Voucher in
``G.GAME.current_round.voucher`` and materializes that center into the separate
``G.shop_vouchers`` card area.  The card uses ordinary ``Card:set_cost`` pricing;
there is no edition on this normal Voucher path.

This module owns only generation/publication metadata.  It deliberately does not
make Voucher redemption effects exact or broaden ``BUY_VOUCHER`` legality.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.shop_voucher_generation import poll_observed_normal_voucher_key
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


@dataclass(frozen=True)
class OrdinaryShopVoucherDescriptor:
    """Exact selected normal Voucher plus authoritative immutable base cost."""

    run: HeadlessRunState
    center_key: str
    base_cost: int
    resamples: int


@dataclass(frozen=True)
class GeneratedShopVoucherItem:
    """Exact public metadata for the ordinary normal-shop Voucher card."""

    center_key: str
    base_cost: int
    price: int

    @property
    def kind(self) -> str:
        return "VOUCHER"

    @property
    def center(self) -> str:
        return self.center_key


def describe_observed_normal_shop_voucher(
    run: HeadlessRunState,
) -> OrdinaryShopVoucherDescriptor:
    """Poll the observed exact Voucher pool and attach its observed center cost."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    # ``poll_observed_normal_voucher_key`` validates the complete observed
    # catalogue before advancing RNG.  Re-read that same canonical catalogue only
    # to attach immutable center metadata to the selected key.
    poll = poll_observed_normal_voucher_key(run)
    records = run.public.voucher_generation_pool

    matches = [record for record in records if record.get("key") == poll.center_key]
    if len(matches) != 1:
        raise HeadlessTransitionError(
            "selected Voucher center is absent from authoritative generation catalogue"
        )
    base_cost = matches[0].get("cost")
    if type(base_cost) is not int or base_cost < 0:
        raise HeadlessTransitionError("selected Voucher center cost is not authoritative")

    return OrdinaryShopVoucherDescriptor(
        run=poll.run,
        center_key=poll.center_key,
        base_cost=base_cost,
        resamples=poll.resamples,
    )


def materialize_normal_shop_voucher_descriptor(
    descriptor: OrdinaryShopVoucherDescriptor,
) -> tuple[HeadlessRunState, GeneratedShopVoucherItem]:
    """Apply exact ordinary Card:set_cost pricing without publishing the card."""
    if not isinstance(descriptor, OrdinaryShopVoucherDescriptor):
        raise TypeError("descriptor must be OrdinaryShopVoucherDescriptor")

    run = descriptor.run
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("Voucher materialization requires active SHOP")
    if not state.shop_inflation_observed:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if not state.shop_discount_percent_observed:
        raise HeadlessTransitionError("shop discount percent is not authoritative")
    if run.tags:
        raise HeadlessTransitionError(
            "normal Voucher materialization does not own active Tag Voucher effects"
        )

    price = vanilla_card_cost(
        descriptor.base_cost,
        edition=None,
        inflation=state.shop_inflation,
        discount_percent=state.shop_discount_percent,
    )
    return run.copy(), GeneratedShopVoucherItem(
        center_key=descriptor.center_key,
        base_cost=descriptor.base_cost,
        price=price,
    )


def insert_generated_shop_voucher_item(
    run: HeadlessRunState,
    item: GeneratedShopVoucherItem,
) -> HeadlessRunState:
    """Publish one ordinary Voucher in its separate canonical shop slot."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(item, GeneratedShopVoucherItem):
        raise TypeError("item must be GeneratedShopVoucherItem")

    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("Voucher publication requires active SHOP")
    if state.shop_vouchers:
        raise HeadlessTransitionError("normal Voucher shop slot is already occupied")

    next_run = run.copy()
    next_run.public.shop_vouchers.append(item)
    return next_run


def generate_observed_normal_shop_voucher(
    run: HeadlessRunState,
) -> tuple[HeadlessRunState, GeneratedShopVoucherItem]:
    """Select, price and atomically publish the one ordinary normal-shop Voucher."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.public.shop_vouchers:
        raise HeadlessTransitionError("normal Voucher shop slot is already occupied")

    descriptor = describe_observed_normal_shop_voucher(run)
    priced_run, item = materialize_normal_shop_voucher_descriptor(descriptor)
    return insert_generated_shop_voucher_item(priced_run, item), item
