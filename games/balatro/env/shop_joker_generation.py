"""Exact descriptor generation for one ordinary base-shop Joker card.

This module composes already-owned vanilla boundaries without inventing a runtime
Joker constructor. It begins after ``create_card_for_shop`` has selected the
slot type ``Joker`` and reproduces the Joker-specific portion of
``create_card(..., key_append='sho')``:

1. rarity poll;
2. authoritative dynamic pool materialization + center identity/resampling;
3. edition poll.

The result is a deterministic descriptor only. Turning a center key into a
specific Python Joker object, pricing it, placing it in public shop inventory,
or purchasing a Negative edition are separate exactness boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_generation import (
    poll_base_shop_joker_edition,
    poll_base_shop_joker_rarity,
)
from games.balatro.env.shop_generation_state import (
    poll_base_shop_joker_center_from_state,
)
from games.balatro.env.transition import HeadlessRunState


@dataclass(frozen=True)
class OrdinaryShopJokerDescriptor:
    run: HeadlessRunState
    center_key: str
    rarity: int
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
    edition_poll = poll_base_shop_joker_edition(center_poll.run)
    return OrdinaryShopJokerDescriptor(
        run=edition_poll.run,
        center_key=center_poll.center_key,
        rarity=rarity_poll.rarity,
        edition=edition_poll.edition,
        resamples=center_poll.resamples,
    )
