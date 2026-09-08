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

from games.balatro.env.joker_centers import joker_rarity_id, vanilla_joker_pool
from games.balatro.env.shop_generation import (
    ShopJokerCenterPoll,
    poll_base_shop_joker_center,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_REQUIRED_RARITY_KEYS = ("1", "2", "3", "4")
_VANILLA_JOKER_KEYS = frozenset(
    key
    for rarity in (1, 2, 3, 4)
    for key in vanilla_joker_pool(rarity)
)


def _showman_present(run: HeadlessRunState) -> bool:
    return any(type(joker).__name__ == "ShowmanJoker" for joker in run.public.jokers)


def _visible_joker_record(run: HeadlessRunState, item) -> dict:
    center_key = getattr(item, "center_key", None) or getattr(item, "center", None)
    if not isinstance(center_key, str) or center_key not in _VANILLA_JOKER_KEYS:
        raise HeadlessTransitionError("visible shop Joker center is not pinned")

    raw_rarity = getattr(item, "rarity", None)
    if isinstance(raw_rarity, str):
        raw_rarity = raw_rarity.title()
    try:
        rarity = joker_rarity_id(raw_rarity)
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError("visible shop Joker rarity is not exact") from exc

    raw_base_cost = getattr(item, "base_cost", None)
    if type(raw_base_cost) is int and raw_base_cost >= 0:
        base_cost = raw_base_cost
    elif (
        isinstance(raw_base_cost, float)
        and raw_base_cost.is_integer()
        and raw_base_cost >= 0
    ):
        base_cost = int(raw_base_cost)
    else:
        # Compatibility for already-captured checkpoints which predate direct
        # Card.base_cost observation. Only a unique inverse is exact; discounted
        # or minimum-price ambiguity remains fail-closed.
        from games.balatro.env.shop_pricing import vanilla_card_cost

        price = getattr(item, "price", None)
        if price is None:
            price = getattr(item, "cost", None)
        if isinstance(price, float) and price.is_integer():
            price = int(price)
        edition = getattr(item, "edition", None)
        if isinstance(edition, str):
            edition = edition.title()
        candidates = [
            candidate
            for candidate in range(21)
            if vanilla_card_cost(
                candidate,
                edition=edition,
                inflation=run.public.shop_inflation,
                discount_percent=run.public.shop_discount_percent,
            )
            == price
        ] if type(price) is int and price >= 0 else []
        if len(candidates) != 1:
            raise HeadlessTransitionError("visible shop Joker base cost is not exact")
        base_cost = candidates[0]

    return {
        "rarity": rarity,
        "key": center_key,
        "cost": base_cost,
        # Ordinary shop generation cannot create a locked non-Legendary Joker.
        # Visibility therefore proves this dynamic predicate was true.
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
    }


def _ordered_joker_records(rarity: int, records_by_key: dict[str, dict]) -> list[dict]:
    return [
        dict(records_by_key[key])
        for key in vanilla_joker_pool(rarity)
        if key in records_by_key
    ]


def restore_removed_shop_jokers_to_generation_pool(
    run: HeadlessRunState,
    removed_jokers,
) -> HeadlessRunState:
    """Re-admit removed visible Jokers before ordinary reroll generation."""
    pools = _validate_observed_joker_generation_pools(run)
    next_run = run.copy()
    if _showman_present(run):
        return next_run

    owned_keys = {
        getattr(joker, "center_key", None) or getattr(joker, "center", None)
        for joker in run.public.jokers
    }
    by_rarity = {
        rarity: {
            record["key"]: dict(record)
            for record in pools[str(rarity)]
        }
        for rarity in (1, 2, 3, 4)
    }
    for item in removed_jokers:
        record = _visible_joker_record(run, item)
        if record["key"] in owned_keys:
            continue
        by_rarity[record["rarity"]].setdefault(record["key"], record)

    next_run.public.joker_generation_pools = {
        str(rarity): _ordered_joker_records(rarity, by_rarity[rarity])
        for rarity in (1, 2, 3, 4)
    }
    return next_run


def suppress_visible_shop_jokers_from_generation_pool(
    run: HeadlessRunState,
    visible_jokers,
) -> HeadlessRunState:
    """Apply vanilla used_jokers suppression to newly visible shop Jokers."""
    pools = _validate_observed_joker_generation_pools(run)
    next_run = run.copy()
    if _showman_present(run):
        return next_run

    visible_keys = {
        _visible_joker_record(run, item)["key"]
        for item in visible_jokers
    }
    next_run.public.joker_generation_pools = {
        rarity: [
            dict(record)
            for record in pools[rarity]
            if record["key"] not in visible_keys
        ]
        for rarity in _REQUIRED_RARITY_KEYS
    }
    return next_run


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
