"""Authoritative live producer for ordinary Tarot/Planet generation eligibility.

Mirrors the relevant ``get_current_pool`` predicates from the pinned vanilla
source. Runtime pool order is mechanics-significant; this observer emits only
currently eligible records in that order, while the headless static catalogue
restores ``UNAVAILABLE`` positions before keyed identity selection.

All mechanics-critical reads are all-or-nothing. ``None`` means callers must keep
consumable generation unobserved rather than guessing profile/runtime state.
"""

from __future__ import annotations

from .joker_generation_pool_observer import (
    _lua_truthy,
    _observe_showman_present,
    _optional_boolean,
    _optional_string,
    _required_nonnegative_integer,
    _required_string,
    _required_table_fields,
)
from .luajit_memory import LuaJITMemoryError, LuaValue
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder
from .process_memory import BalatroProcessMemoryError


_TYPES = ("Tarot", "Planet")


def observe_consumable_generation_pools(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
) -> dict[str, list[dict[str, object]]] | None:
    """Return exact currently eligible Tarot/Planet records, or ``None``."""
    try:
        game = _required_table_fields(decoder, root.get("GAME"))
        used_jokers = _required_table_fields(decoder, game.get("used_jokers"))
        pool_flags = _required_table_fields(decoder, game.get("pool_flags"))
        banned_keys = _required_table_fields(decoder, game.get("banned_keys"))
        hands = _required_table_fields(decoder, game.get("hands"))
        showman_present = _observe_showman_present(decoder, root.get("jokers"))
        pools = _read_center_pools(decoder, root.get("P_CENTER_POOLS"))

        result: dict[str, list[dict[str, object]]] = {}
        for card_type in _TYPES:
            eligible: list[dict[str, object]] = []
            for center_value in pools[card_type]:
                center = _required_table_fields(decoder, center_value)
                key = _required_string(center.get("key"))
                cost = _required_nonnegative_integer(
                    center.get("cost"), f"{card_type} center cost"
                )
                unlocked = _optional_boolean(center.get("unlocked"))
                no_pool_flag = _optional_string(center.get("no_pool_flag"))
                yes_pool_flag = _optional_string(center.get("yes_pool_flag"))

                add = unlocked is not False
                if add and _lua_truthy(used_jokers.get(key)) and not showman_present:
                    add = False

                softlock = False
                hand_type: str | None = None
                if card_type == "Planet":
                    config = _required_table_fields(decoder, center.get("config"))
                    softlock_value = config.get("softlock")
                    if softlock_value is not None and softlock_value.kind != "nil":
                        if softlock_value.kind != "boolean":
                            raise LuaJITMemoryError("Planet softlock is not a boolean")
                        softlock = bool(softlock_value.value)
                    if softlock:
                        hand_type = _required_string(config.get("hand_type"))
                        hand = _required_table_fields(decoder, hands.get(hand_type))
                        played = _required_nonnegative_integer(
                            hand.get("played"), "Planet softlock hand played count"
                        )
                        if played <= 0:
                            add = False

                if no_pool_flag is not None and _lua_truthy(pool_flags.get(no_pool_flag)):
                    add = False
                if yes_pool_flag is not None and not _lua_truthy(pool_flags.get(yes_pool_flag)):
                    add = False
                if _lua_truthy(banned_keys.get(key)):
                    add = False

                if add:
                    eligible.append(
                        {
                            "type": card_type,
                            "key": key,
                            "cost": cost,
                            "unlocked": unlocked,
                            "no_pool_flag": no_pool_flag,
                            "yes_pool_flag": yes_pool_flag,
                            "softlock": softlock,
                            "hand_type": hand_type,
                        }
                    )
            result[card_type] = eligible
        return result
    except (BalatroProcessMemoryError, LuaJITMemoryError, KeyError, TypeError, ValueError):
        return None


def _read_center_pools(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, list[LuaValue]]:
    fields = _required_table_fields(decoder, value)
    result: dict[str, list[LuaValue]] = {}
    for card_type in _TYPES:
        pool_value = fields.get(card_type)
        if pool_value is None or pool_value.kind != "table":
            raise LuaJITMemoryError(f"G.P_CENTER_POOLS.{card_type} is unavailable")
        entries = decoder.array_items_strict(int(pool_value.value))
        centers: list[LuaValue] = []
        for _, center_value in entries:
            if center_value.kind != "table":
                raise LuaJITMemoryError(
                    f"{card_type} generation pool contains a non-table center"
                )
            centers.append(center_value)
        result[card_type] = centers
    return result
