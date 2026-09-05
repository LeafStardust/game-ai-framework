"""Exact descriptor generation for one ordinary base-shop Joker card.

This module composes already-owned vanilla boundaries without inventing a runtime
Joker constructor. It begins after ``create_card_for_shop`` has selected the
slot type ``Joker`` and reproduces the Joker-specific portion of
``create_card(..., key_append='sho')``:

1. rarity poll;
2. authoritative dynamic pool materialization + center identity/resampling;
3. immutable center base-cost lookup from that same authoritative pool;
4. edition poll.

The result is a deterministic descriptor only. Pricing, placement in public shop
inventory, runtime strategy-object construction, and purchase legality remain
separate exactness boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_generation import (
    poll_base_shop_joker_edition,
    poll_base_shop_joker_rarity,
)
from games.balatro.env.shop_generation_state import (
    joker_center_cost_from_state,
    poll_base_shop_joker_center_from_state,
)
from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class OrdinaryShopJokerDescriptor:
    run: HeadlessRunState
    center_key: str
    rarity: int
    base_cost: int
    edition: str | None
    resamples: int


def generate_ordinary_shop_joker_descriptor(
    run: HeadlessRunState,
) -> OrdinaryShopJokerDescriptor:
    """Generate one source-ordered ordinary base-shop Joker descriptor."""
    rarity_poll = poll_base_shop_joker_rarity(run)
    center_poll = poll_base_shop_joker_center_from_state(
        rarity_poll.run,
        rarity_poll.rarity,
    )
    base_cost = joker_center_cost_from_state(
        center_poll.run,
        rarity_poll.rarity,
        center_poll.center_key,
    )
    edition_poll = poll_base_shop_joker_edition(center_poll.run)
    return OrdinaryShopJokerDescriptor(
        run=edition_poll.run,
        center_key=center_poll.center_key,
        rarity=rarity_poll.rarity,
        base_cost=base_cost,
        edition=edition_poll.edition,
        resamples=center_poll.resamples,
    )
