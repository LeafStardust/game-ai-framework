"""Canonical-state bridge into exact R2 shop Joker identity RNG.

Dynamic eligibility is observed/translated into :class:`BalatroState`. The RNG
owner in ``shop_generation`` deliberately accepts only explicit eligible keys.
This module is the narrow adapter between those two existing contracts; it does
not reimplement pool filtering or identity RNG.

The whole canonical catalogue is validated before any rarity is consumed. Each
record also carries the exact immutable center ``cost`` needed by the downstream
``Card:set_cost`` boundary.
"""

from __future__ import annotations

from games.balatro.env.shop_generation import (
    ShopJokerCenterPoll,
    poll_base_shop_joker_center,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_REQUIRED_RARITY_KEYS = ("1", "2", "3", "4")


def _validate_observed_joker_generation_pools(run: HeadlessRunState) -> dict[str, list[dict]]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if not state.joker_generation_pool_observed:
        raise HeadlessTransitionError("Joker generation pool is not authoritatively observed")

    pools = state.joker_generation_pools
    if not isinstance(pools, dict) or set(pools) != set(_REQUIRED_RARITY_KEYS):
        raise HeadlessTransitionError(
            "authoritative Joker generation pool must contain exact rarities 1 through 4"
        )

    seen_keys: set[str] = set()
    for rarity_key in _REQUIRED_RARITY_KEYS:
        records = pools[rarity_key]
        if not isinstance(records, list):
            raise HeadlessTransitionError(
                "authoritative Joker generation rarity pool must be a list"
            )
        rarity = int(rarity_key)
        for record in records:
            if not isinstance(record, dict):
                raise HeadlessTransitionError("Joker generation pool record must be a mapping")
            if type(record.get("rarity")) is not int or record["rarity"] != rarity:
                raise HeadlessTransitionError("Joker generation pool record rarity mismatch")

            key = record.get("key")
            if not isinstance(key, str) or not key:
                raise HeadlessTransitionError("Joker generation pool record has invalid center key")
            if key in seen_keys:
                raise HeadlessTransitionError("Joker generation pool contains duplicate center keys")
            seen_keys.add(key)

            cost = record.get("cost")
            if type(cost) is not int or cost < 0:
                raise HeadlessTransitionError(
                    "Joker generation pool record has invalid center cost"
                )

            unlocked = record.get("unlocked")
            if unlocked is not None and not isinstance(unlocked, bool):
                raise HeadlessTransitionError("Joker generation pool record has invalid unlocked state")
            for flag_name in ("no_pool_flag", "yes_pool_flag"):
                flag = record.get(flag_name)
                if flag is not None and (not isinstance(flag, str) or not flag):
                    raise HeadlessTransitionError(
                        f"Joker generation pool record has invalid {flag_name}"
                    )

    return pools


def eligible_joker_keys_from_state(run: HeadlessRunState, rarity: int) -> tuple[str, ...]:
    """Return one exact observed rarity's eligible center keys or fail closed."""
    if type(rarity) is not int or rarity not in (1, 2, 3, 4):
        raise HeadlessTransitionError("Joker rarity must be exact 1, 2, 3, or 4")

    pools = _validate_observed_joker_generation_pools(run)
    records = pools[str(rarity)]
    return tuple(record["key"] for record in records)


def joker_center_cost_from_state(run: HeadlessRunState, rarity: int, center_key: str) -> int:
    """Return the exact observed immutable base cost for one eligible center."""
    if type(rarity) is not int or rarity not in (1, 2, 3, 4):
        raise HeadlessTransitionError("Joker rarity must be exact 1, 2, 3, or 4")
    if not isinstance(center_key, str) or not center_key:
        raise HeadlessTransitionError("Joker center key must be a nonempty string")

    pools = _validate_observed_joker_generation_pools(run)
    for record in pools[str(rarity)]:
        if record["key"] == center_key:
            return record["cost"]
    raise HeadlessTransitionError(
        "selected Joker center is absent from the authoritative eligible pool"
    )


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
