"""Canonical-state bridge into exact Tarot/Planet shop generation.

The live observer and translator own dynamic eligibility. This module validates
that canonical observation all-or-nothing before any RNG-consuming shop poll.
Both Tarot and Planet catalogues must be present even when only one type is being
selected; accepting a partially translated observation would weaken the runtime
boundary.
"""

from __future__ import annotations

from games.balatro.env.shop_consumable_items import (
    OrdinaryShopConsumableDescriptor,
    describe_base_shop_consumable_from_records,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_REQUIRED_TYPES = ("Tarot", "Planet")


def _validate_observed_consumable_generation_pools(
    run: HeadlessRunState,
) -> dict[str, list[dict]]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if not isinstance(state.consumable_generation_pool_observed, bool):
        raise HeadlessTransitionError(
            "consumable_generation_pool_observed must be a boolean"
        )
    if not state.consumable_generation_pool_observed:
        raise HeadlessTransitionError(
            "Tarot/Planet generation pool is not authoritatively observed"
        )

    pools = state.consumable_generation_pools
    if not isinstance(pools, dict) or set(pools) != set(_REQUIRED_TYPES):
        raise HeadlessTransitionError(
            "authoritative consumable generation pool must contain exact Tarot and Planet catalogues"
        )

    seen_keys: set[str] = set()
    validated: dict[str, list[dict]] = {}
    for card_type in _REQUIRED_TYPES:
        records = pools[card_type]
        if not isinstance(records, list):
            raise HeadlessTransitionError(
                "authoritative consumable generation catalogue must be a list"
            )
        copied: list[dict] = []
        for record in records:
            if not isinstance(record, dict):
                raise HeadlessTransitionError(
                    "consumable generation pool record must be a mapping"
                )
            if record.get("type") != card_type:
                raise HeadlessTransitionError(
                    "consumable generation pool record type mismatch"
                )
            key = record.get("key")
            if not isinstance(key, str) or not key:
                raise HeadlessTransitionError(
                    "consumable generation pool record has invalid center key"
                )
            if key in seen_keys:
                raise HeadlessTransitionError(
                    "consumable generation pool contains duplicate center keys"
                )
            seen_keys.add(key)

            cost = record.get("cost")
            if type(cost) is not int or cost < 0:
                raise HeadlessTransitionError(
                    "consumable generation pool record has invalid center cost"
                )
            unlocked = record.get("unlocked")
            if unlocked is not None and not isinstance(unlocked, bool):
                raise HeadlessTransitionError(
                    "consumable generation pool record has invalid unlocked state"
                )
            for flag_name in ("no_pool_flag", "yes_pool_flag"):
                flag = record.get(flag_name)
                if flag is not None and (not isinstance(flag, str) or not flag):
                    raise HeadlessTransitionError(
                        f"consumable generation pool record has invalid {flag_name}"
                    )
            softlock = record.get("softlock")
            if not isinstance(softlock, bool):
                raise HeadlessTransitionError(
                    "consumable generation pool record has invalid softlock state"
                )
            hand_type = record.get("hand_type")
            if hand_type is not None and (not isinstance(hand_type, str) or not hand_type):
                raise HeadlessTransitionError(
                    "consumable generation pool record has invalid hand_type"
                )
            if card_type == "Tarot" and (softlock or hand_type is not None):
                raise HeadlessTransitionError(
                    "Tarot generation record cannot carry Planet softlock metadata"
                )
            if card_type == "Planet" and softlock and hand_type is None:
                raise HeadlessTransitionError(
                    "softlocked Planet generation record requires hand_type"
                )
            copied.append(dict(record))
        validated[card_type] = copied

    return validated


def eligible_consumable_records_from_state(
    run: HeadlessRunState,
    card_type: str,
) -> tuple[dict, ...]:
    if card_type not in _REQUIRED_TYPES:
        raise HeadlessTransitionError("ordinary consumable type must be Tarot or Planet")
    pools = _validate_observed_consumable_generation_pools(run)
    return tuple(dict(record) for record in pools[card_type])


def generate_ordinary_shop_consumable_descriptor_from_state(
    run: HeadlessRunState,
    card_type: str,
) -> OrdinaryShopConsumableDescriptor:
    """Generate one exact Tarot/Planet descriptor from canonical eligibility."""
    records = eligible_consumable_records_from_state(run, card_type)
    return describe_base_shop_consumable_from_records(run, card_type, records)
