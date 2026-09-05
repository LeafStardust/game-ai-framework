"""Canonical headless representations for generated shop inventory.

A generated shop Joker is not automatically a mechanically executable Joker
instance.  Shop generation first owns public item identity, rarity, edition, and
purchase price.  Strategy/runtime Joker construction and acquisition semantics are
separate boundaries and remain fail-closed independently.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.shop_pricing import price_base_shop_joker_descriptor
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_BASE_MAIN_SHOP_SLOTS = 2


@dataclass(frozen=True)
class GeneratedShopJokerItem:
    """Exact public shop metadata for one generated ordinary Joker card."""

    center_key: str
    rarity: int
    base_cost: int
    edition: str | None
    price: int

    @property
    def kind(self) -> str:
        return "JOKER"

    @property
    def center(self) -> str:
        return self.center_key


def materialize_shop_joker_descriptor(
    descriptor: OrdinaryShopJokerDescriptor,
) -> tuple[HeadlessRunState, GeneratedShopJokerItem]:
    """Materialize exact public metadata without constructing a gameplay Joker.

    The returned run is the descriptor's post-generation snapshot.  It is copied
    so later inventory insertion cannot mutate the descriptor's retained replay
    state.  This function intentionally does not append the item to ``shop_jokers``
    and does not make BUY_JOKER legal.
    """
    if not isinstance(descriptor, OrdinaryShopJokerDescriptor):
        raise TypeError("descriptor must be OrdinaryShopJokerDescriptor")

    center_key = descriptor.center_key
    if not isinstance(center_key, str) or not center_key:
        raise HeadlessTransitionError("generated Joker center key must be nonempty")
    if type(descriptor.rarity) is not int or descriptor.rarity not in (1, 2, 3):
        raise HeadlessTransitionError("generated Joker rarity must be exact 1, 2, or 3")
    if type(descriptor.base_cost) is not int or descriptor.base_cost < 0:
        raise HeadlessTransitionError("generated Joker base cost must be a nonnegative exact integer")

    price = price_base_shop_joker_descriptor(descriptor)
    item = GeneratedShopJokerItem(
        center_key=center_key,
        rarity=descriptor.rarity,
        base_cost=descriptor.base_cost,
        edition=descriptor.edition,
        price=price,
    )
    return descriptor.run.copy(), item


def insert_generated_shop_joker_item(
    run: HeadlessRunState,
    item: GeneratedShopJokerItem,
) -> HeadlessRunState:
    """Insert one exact generated Joker card into the public main-shop area.

    The current canonical state stores main-shop Jokers and consumables in
    category-specific lists, so the shared vanilla two-card area capacity is
    enforced by the sum of those lists.  This operation owns placement only; it
    intentionally does not convert the metadata item into a gameplay Joker and
    therefore does not widen BUY_JOKER legality.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(item, GeneratedShopJokerItem):
        raise TypeError("item must be GeneratedShopJokerItem")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("generated shop insertion requires active SHOP")
    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied >= _BASE_MAIN_SHOP_SLOTS:
        raise HeadlessTransitionError("main shop inventory is already full")

    next_run = run.copy()
    next_run.public.shop_jokers.append(item)
    return next_run
