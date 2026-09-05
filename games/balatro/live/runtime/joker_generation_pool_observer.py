"""Authoritative live producer for vanilla Joker-generation eligibility.

This module mirrors only the dynamic eligibility predicates from Balatro's
``get_current_pool('Joker', rarity, ...)``.  Static center ordering remains owned
by the running game's ``G.P_JOKER_RARITY_POOLS``; the headless static catalogue
is not used to guess profile/runtime eligibility.

Any incomplete mechanics-critical table read returns ``None``.  Callers must then
report ``joker_generation_pool_observed = False``.
"""

from __future__ import annotations

from .luajit_memory import LuaJITMemoryError, LuaValue
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder
from .luajit_strict_tables import string_fields_strict
from .process_memory import BalatroProcessMemoryError


_REQUIRED_RARITIES = (1, 2, 3, 4)
_SHOWMAN_CENTER = "j_showman"


def observe_joker_generation_pools(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
) -> dict[int, list[str]] | None:
    """Return exact currently eligible Joker center keys by rarity, or ``None``.

    The returned lists preserve the live game's rarity-pool order while omitting
    entries that vanilla would replace with ``UNAVAILABLE``.  The headless pool
    owner later restores those unavailable positions against its audited static
    rarity catalogue before consuming identity RNG.
    """

    try:
        game = _required_table_fields(decoder, root.get("GAME"))
        used_jokers = _required_table_fields(decoder, game.get("used_jokers"))
        pool_flags = _required_table_fields(decoder, game.get("pool_flags"))
        banned_keys = _required_table_fields(decoder, game.get("banned_keys"))
        showman_present = _observe_showman_present(decoder, root.get("jokers"))
        rarity_pools = _read_rarity_pools(
            decoder,
            root.get("P_JOKER_RARITY_POOLS"),
        )

        result: dict[int, list[str]] = {}
        for rarity in _REQUIRED_RARITIES:
            eligible: list[str] = []
            for center_value in rarity_pools[rarity]:
                center = _required_table_fields(decoder, center_value)
                key = _required_string(center.get("key"))

                unlocked = center.get("unlocked")
                if rarity != 4 and _explicit_false(unlocked):
                    continue

                if _lua_truthy(used_jokers.get(key)) and not showman_present:
                    continue

                no_pool_flag = _optional_string(center.get("no_pool_flag"))
                if no_pool_flag is not None and _lua_truthy(pool_flags.get(no_pool_flag)):
                    continue

                yes_pool_flag = _optional_string(center.get("yes_pool_flag"))
                if yes_pool_flag is not None and not _lua_truthy(pool_flags.get(yes_pool_flag)):
                    continue

                if _lua_truthy(banned_keys.get(key)):
                    continue

                eligible.append(key)

            result[rarity] = eligible
        return result
    except (BalatroProcessMemoryError, LuaJITMemoryError, KeyError, TypeError, ValueError):
        return None


def _required_table_fields(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[str, LuaValue]:
    if value is None or value.kind != "table":
        raise LuaJITMemoryError("required runtime value is not a Lua table")
    return string_fields_strict(decoder, int(value.value))


def _read_rarity_pools(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> dict[int, list[LuaValue]]:
    if value is None or value.kind != "table":
        raise LuaJITMemoryError("G.P_JOKER_RARITY_POOLS is unavailable")

    outer = decoder.array_items_strict(int(value.value))
    by_index = {index: item for index, item in outer if item.kind != "nil"}
    result: dict[int, list[LuaValue]] = {}
    for rarity in _REQUIRED_RARITIES:
        pool_value = by_index.get(rarity)
        if pool_value is None or pool_value.kind != "table":
            raise LuaJITMemoryError(f"Joker rarity pool {rarity} is unavailable")
        entries = decoder.array_items_strict(int(pool_value.value))
        centers: list[LuaValue] = []
        for _, center_value in entries:
            if center_value.kind != "table":
                raise LuaJITMemoryError(
                    f"Joker rarity pool {rarity} contains a non-table center"
                )
            centers.append(center_value)
        result[rarity] = centers
    return result


def _observe_showman_present(
    decoder: LuaJITNonGC64Decoder,
    jokers_value: LuaValue | None,
) -> bool:
    area = _required_table_fields(decoder, jokers_value)
    cards_value = area.get("cards")
    if cards_value is None or cards_value.kind != "table":
        raise LuaJITMemoryError("G.jokers.cards is unavailable")

    for _, card_value in decoder.array_items_strict(int(cards_value.value)):
        if card_value.kind != "table":
            raise LuaJITMemoryError("G.jokers.cards contains a non-table value")
        card = _required_table_fields(decoder, card_value)
        config = _required_table_fields(decoder, card.get("config"))
        center = _required_table_fields(decoder, config.get("center"))
        if _required_string(center.get("key")) == _SHOWMAN_CENTER:
            return True
    return False


def _required_string(value: LuaValue | None) -> str:
    if value is None or value.kind != "string" or not str(value.value):
        raise LuaJITMemoryError("required runtime string is unavailable")
    return str(value.value)


def _optional_string(value: LuaValue | None) -> str | None:
    if value is None:
        return None
    if value.kind != "string":
        raise LuaJITMemoryError("optional runtime flag is not a string")
    text = str(value.value)
    if not text:
        raise LuaJITMemoryError("optional runtime flag is empty")
    return text


def _explicit_false(value: LuaValue | None) -> bool:
    return value is not None and value.kind == "boolean" and value.value is False


def _lua_truthy(value: LuaValue | None) -> bool:
    if value is None or value.kind == "nil":
        return False
    if value.kind == "boolean" and value.value is False:
        return False
    return True
