"""Canonical-state bridge into exact R2 shop Joker identity RNG.

Dynamic eligibility is observed/translated into :class:`BalatroState`.  The RNG
owner in ``shop_generation`` deliberately accepts only explicit eligible keys.
This module is the narrow adapter between those two existing contracts; it does
not reimplement pool filtering or identity RNG.
"""

from __future__ import annotations

from games.balatro.env.shop_generation import (
    ShopJokerCenterPoll,
    poll_base_shop_joker_center,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def eligible_joker_keys_from_state(run: HeadlessRunState, rarity: int) -> tuple[str, ...]:
    """Return one exact observed rarity's eligible center keys or fail closed."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(rarity) is not int or rarity not in (1, 2, 3, 4):
        raise HeadlessTransitionError("Joker rarity must be exact 1, 2, 3, or 4")

    state = run.public
    if not state.joker_generation_pool_observed:
        raise HeadlessTransitionError("Joker generation pool is not authoritatively observed")
    pools = state.joker_generation_pools
    rarity_key = str(rarity)
    if not isinstance(pools, dict) or rarity_key not in pools:
        raise HeadlessTransitionError(
            f"authoritative Joker generation pool is missing rarity {rarity}"
        )
    records = pools[rarity_key]
    if not isinstance(records, list):
        raise HeadlessTransitionError("authoritative Joker generation rarity pool must be a list")

    keys: list[str] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise HeadlessTransitionError("Joker generation pool record must be a mapping")
        if record.get("rarity") != rarity:
            raise HeadlessTransitionError("Joker generation pool record rarity mismatch")
        key = record.get("key")
        if not isinstance(key, str) or not key:
            raise HeadlessTransitionError("Joker generation pool record has invalid center key")
        if key in seen:
            raise HeadlessTransitionError("Joker generation pool contains duplicate center keys")
        seen.add(key)
        keys.append(key)

    return tuple(keys)


def poll_base_shop_joker_center_from_state(
    run: HeadlessRunState,
    rarity: int,
) -> ShopJokerCenterPoll:
    """Select an exact shop Joker identity from canonical observed eligibility."""
    eligible_keys = eligible_joker_keys_from_state(run, rarity)
    try:
        return poll_base_shop_joker_center(run, rarity, eligible_keys)
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError(
            "observed Joker generation pool is incompatible with the pinned vanilla catalogue"
        ) from exc
