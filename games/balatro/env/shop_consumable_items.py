"""Exact Tarot/Planet shop descriptor pricing and materialization.

This module deliberately keeps live/runtime eligibility records explicit.  The
normal live observer already produces authoritative eligible Tarot/Planet records;
this layer validates that record set all-or-nothing, performs the existing exact
identity poll, carries the selected center's observed immutable base cost, and
applies vanilla ``Card:set_cost`` pricing with no edition surcharge.

Gameplay-object construction and purchase legality remain separate exactness
boundaries.  Generated metadata may be inserted into the shared two-card main
shop only after its source-ordered generation is complete.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from games.balatro.env.shop_consumable_generation import (
    ShopConsumableCenterPoll,
    poll_base_shop_consumable_center,
)
from games.balatro.env.shop_pricing import vanilla_card_cost
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_FALLBACK_BASE_COST = {
    "Tarot": 3,   # c_strength in pinned vanilla source
    "Planet": 3,  # c_pluto in pinned vanilla source
}
_BASE_MAIN_SHOP_SLOTS = 2


@dataclass(frozen=True)
class OrdinaryShopConsumableDescriptor:
    """Exact post-RNG ordinary Tarot/Planet descriptor before shop insertion."""

    run: HeadlessRunState
    card_type: str
    center_key: str
    base_cost: int
    resamples: int


@dataclass(frozen=True)
class GeneratedShopConsumableItem:
    """Exact public metadata for one generated ordinary Tarot/Planet shop card."""

    card_type: str
    center_key: str
    base_cost: int
    price: int

    @property
    def kind(self) -> str:
        return "CONSUMABLE"

    @property
    def center(self) -> str:
        return self.center_key


def _validated_eligible_records(
    card_type: str,
    records: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    if card_type not in ("Tarot", "Planet"):
        raise HeadlessTransitionError("ordinary consumable type must be Tarot or Planet")
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise HeadlessTransitionError("authoritative consumable generation records must be a sequence")

    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise HeadlessTransitionError("consumable generation record must be a mapping")
        if record.get("type") != card_type:
            raise HeadlessTransitionError("consumable generation record type mismatch")

        key = record.get("key")
        if not isinstance(key, str) or not key:
            raise HeadlessTransitionError("consumable generation record has invalid center key")
        if key in seen:
            raise HeadlessTransitionError("consumable generation pool contains duplicate center keys")
        seen.add(key)

        cost = record.get("cost")
        if type(cost) is not int or cost < 0:
            raise HeadlessTransitionError("consumable generation record has invalid center cost")

        unlocked = record.get("unlocked")
        if unlocked is not None and not isinstance(unlocked, bool):
            raise HeadlessTransitionError("consumable generation record has invalid unlocked state")

        for flag_name in ("no_pool_flag", "yes_pool_flag"):
            flag = record.get(flag_name)
            if flag is not None and (not isinstance(flag, str) or not flag):
                raise HeadlessTransitionError(
                    f"consumable generation record has invalid {flag_name}"
                )

        softlock = record.get("softlock")
        if not isinstance(softlock, bool):
            raise HeadlessTransitionError("consumable generation record has invalid softlock state")
        hand_type = record.get("hand_type")
        if hand_type is not None and (not isinstance(hand_type, str) or not hand_type):
            raise HeadlessTransitionError("consumable generation record has invalid hand_type")
        if card_type == "Tarot" and (softlock or hand_type is not None):
            raise HeadlessTransitionError("Tarot generation record cannot carry Planet softlock metadata")
        if card_type == "Planet" and softlock and hand_type is None:
            raise HeadlessTransitionError("softlocked Planet generation record requires hand_type")

        result.append(dict(record))

    return tuple(result)


def describe_base_shop_consumable_from_records(
    run: HeadlessRunState,
    card_type: str,
    records: Sequence[dict[str, object]],
) -> OrdinaryShopConsumableDescriptor:
    """Poll one exact identity and attach its authoritative immutable base cost."""
    validated = _validated_eligible_records(card_type, records)
    eligible_keys = tuple(record["key"] for record in validated)

    # Validation precedes RNG consumption so malformed observation never advances
    # replay state.
    poll = poll_base_shop_consumable_center(run, card_type, eligible_keys)

    cost_by_key = {record["key"]: record["cost"] for record in validated}
    if poll.center_key in cost_by_key:
        base_cost = cost_by_key[poll.center_key]
    elif not validated:
        # Vanilla get_current_pool falls back to Strength/Pluto when every source
        # position is unavailable. Both centers have pinned base cost 3.
        base_cost = _FALLBACK_BASE_COST[card_type]
    else:
        raise HeadlessTransitionError(
            "selected consumable center is absent from authoritative eligible records"
        )

    assert type(base_cost) is int
    return OrdinaryShopConsumableDescriptor(
        run=poll.run,
        card_type=poll.card_type,
        center_key=poll.center_key,
        base_cost=base_cost,
        resamples=poll.resamples,
    )


def materialize_base_shop_consumable_descriptor(
    descriptor: OrdinaryShopConsumableDescriptor,
) -> tuple[HeadlessRunState, GeneratedShopConsumableItem]:
    """Price exact ordinary Tarot/Planet metadata without inserting inventory."""
    if not isinstance(descriptor, OrdinaryShopConsumableDescriptor):
        raise TypeError("descriptor must be OrdinaryShopConsumableDescriptor")

    run = descriptor.run
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("consumable materialization requires active SHOP")
    if not state.shop_inflation_observed:
        raise HeadlessTransitionError("shop inflation is not authoritative")
    if not state.shop_discount_percent_observed:
        raise HeadlessTransitionError("shop discount percent is not authoritative")
    if state.vouchers:
        raise HeadlessTransitionError("base consumable materialization does not own voucher modifiers")
    if run.tags:
        raise HeadlessTransitionError("base consumable materialization does not own active Tag effects")

    price = vanilla_card_cost(
        descriptor.base_cost,
        edition=None,
        inflation=state.shop_inflation,
        discount_percent=state.shop_discount_percent,
    )
    item = GeneratedShopConsumableItem(
        card_type=descriptor.card_type,
        center_key=descriptor.center_key,
        base_cost=descriptor.base_cost,
        price=price,
    )
    return run.copy(), item


def insert_generated_shop_consumable_item(
    run: HeadlessRunState,
    item: GeneratedShopConsumableItem,
) -> HeadlessRunState:
    """Insert one generated Tarot/Planet item into the shared main-shop area.

    Canonical state stores main-shop Jokers and consumables in separate public
    lists, while vanilla stores both in ``G.shop_jokers``.  Capacity is therefore
    enforced by the sum of those lists.  This owns placement only and does not
    make BUY_CONSUMABLE legal for generated metadata.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(item, GeneratedShopConsumableItem):
        raise TypeError("item must be GeneratedShopConsumableItem")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("generated shop insertion requires active SHOP")
    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied >= _BASE_MAIN_SHOP_SLOTS:
        raise HeadlessTransitionError("main shop inventory is already full")

    next_run = run.copy()
    next_run.public.shop_consumables.append(item)
    return next_run
