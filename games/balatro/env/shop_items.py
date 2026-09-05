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
