"""Canonical-state bridge into exact Tarot/Planet shop generation.

The live observer and translator own dynamic eligibility. This module validates
that canonical observation all-or-nothing before any RNG-consuming shop poll.
Both Tarot and Planet catalogues must be present even when only one type is being
selected; accepting a partially translated observation would weaken the runtime
boundary.

Ordinary shop visibility participates in Balatro's duplicate suppression through
``G.GAME.used_jokers``. A visible Tarot/Planet card is absent from the current
eligible pool unless Showman is active; removing that card can make it eligible
again before the next shop generation. The lifecycle helpers below update only
that exact visibility effect. Other unlock/flag/softlock predicates remain owned
by the authoritative observed records and are never guessed.
"""

from __future__ import annotations

from games.balatro.env.consumable_centers import vanilla_consumable_center_order
from games.balatro.env.shop_consumable_items import (
    OrdinaryShopConsumableDescriptor,
    describe_base_shop_consumable_from_records,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_REQUIRED_TYPES = ("Tarot", "Planet")

_TAROT_NAME_TO_KEY = {
    "The Fool": "c_fool",
    "The Magician": "c_magician",
    "The High Priestess": "c_high_priestess",
    "The Empress": "c_empress",
    "The Emperor": "c_emperor",
    "The Hierophant": "c_heirophant",
    "The Lovers": "c_lovers",
    "The Chariot": "c_chariot",
    "Justice": "c_justice",
    "The Hermit": "c_hermit",
    "The Wheel of Fortune": "c_wheel_of_fortune",
    "Strength": "c_strength",
    "The Hanged Man": "c_hanged_man",
    "Death": "c_death",
    "Temperance": "c_temperance",
    "The Devil": "c_devil",
    "The Tower": "c_tower",
    "The Star": "c_star",
    "The Moon": "c_moon",
    "The Sun": "c_sun",
    "Judgement": "c_judgement",
    "The World": "c_world",
}

_PLANET_NAME_TO_KEY = {
    "Mercury": "c_mercury",
    "Venus": "c_venus",
    "Earth": "c_earth",
    "Mars": "c_mars",
    "Jupiter": "c_jupiter",
    "Saturn": "c_saturn",
    "Uranus": "c_uranus",
    "Neptune": "c_neptune",
    "Pluto": "c_pluto",
    "Planet X": "c_planet_x",
    "Ceres": "c_ceres",
    "Eris": "c_eris",
}

_SECRET_PLANET_HAND_TYPES = {
    "c_planet_x": "FIVE_OF_A_KIND",
    "c_ceres": "FLUSH_HOUSE",
    "c_eris": "FLUSH_FIVE",
}


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


def _showman_present(run: HeadlessRunState) -> bool:
    return any(type(joker).__name__ == "ShowmanJoker" for joker in run.public.jokers)


def _visible_consumable_record(item) -> dict | None:
    """Reconstruct exact static generation metadata for one visible Tarot/Planet.

    Presence in the shop/owned consumable area already proves the center passed
    its dynamic unlock/flag/softlock predicates when it was created. During an
    ordinary paid reroll none of those predicates change; only duplicate
    visibility changes. Vanilla Tarot/Planet base cost is 3. Secret Planets carry
    their pinned softlock hand metadata.
    """
    explicit_type = getattr(item, "card_type", None)
    explicit_key = getattr(item, "center_key", None)
    if explicit_type in _REQUIRED_TYPES and isinstance(explicit_key, str):
        card_type = explicit_type
        key = explicit_key
        base_cost = getattr(item, "base_cost", 3)
        if type(base_cost) is not int or base_cost < 0:
            raise HeadlessTransitionError("visible consumable base cost is not exact")
    else:
        category = str(getattr(item, "category", "")).upper()
        name = getattr(item, "name", None)
        if not isinstance(name, str) or not name:
            return None
        if category == "TAROT":
            card_type = "Tarot"
            key = _TAROT_NAME_TO_KEY.get(name)
        elif category == "PLANET":
            card_type = "Planet"
            key = _PLANET_NAME_TO_KEY.get(name)
        else:
            return None
        if key is None:
            raise HeadlessTransitionError("visible consumable center is not pinned")
        base_cost = 3

    if key not in vanilla_consumable_center_order(card_type):
        raise HeadlessTransitionError("visible consumable center is outside pinned vanilla order")

    hand_type = _SECRET_PLANET_HAND_TYPES.get(key)
    return {
        "type": card_type,
        "key": key,
        "cost": base_cost,
        "unlocked": None,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": hand_type is not None,
        "hand_type": hand_type,
    }


def _ordered_records(card_type: str, records_by_key: dict[str, dict]) -> list[dict]:
    order = vanilla_consumable_center_order(card_type)
    return [dict(records_by_key[key]) for key in order if key in records_by_key]


def restore_removed_shop_consumables_to_generation_pool(
    run: HeadlessRunState,
    removed_consumables,
) -> HeadlessRunState:
    """Re-admit removed visible Tarot/Planet cards before reroll generation."""
    pools = _validate_observed_consumable_generation_pools(run)
    next_run = run.copy()
    if _showman_present(run):
        return next_run

    held_keys = {
        record["key"]
        for item in run.public.consumables
        if (record := _visible_consumable_record(item)) is not None
    }
    by_type = {
        card_type: {record["key"]: dict(record) for record in pools[card_type]}
        for card_type in _REQUIRED_TYPES
    }
    for item in removed_consumables:
        record = _visible_consumable_record(item)
        if record is None or record["key"] in held_keys:
            continue
        by_type[record["type"]].setdefault(record["key"], record)

    next_run.public.consumable_generation_pools = {
        card_type: _ordered_records(card_type, by_type[card_type])
        for card_type in _REQUIRED_TYPES
    }
    return next_run


def suppress_visible_shop_consumables_from_generation_pool(
    run: HeadlessRunState,
    visible_consumables,
) -> HeadlessRunState:
    """Apply vanilla duplicate suppression for newly visible shop consumables."""
    pools = _validate_observed_consumable_generation_pools(run)
    next_run = run.copy()
    if _showman_present(run):
        return next_run

    visible_keys = {
        record["key"]
        for item in visible_consumables
        if (record := _visible_consumable_record(item)) is not None
    }
    next_run.public.consumable_generation_pools = {
        card_type: [
            dict(record)
            for record in pools[card_type]
            if record["key"] not in visible_keys
        ]
        for card_type in _REQUIRED_TYPES
    }
    return next_run


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
