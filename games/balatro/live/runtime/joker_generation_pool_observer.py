"""Authoritative live producer for vanilla Joker-generation eligibility.

This module mirrors the dynamic eligibility predicates from Balatro's
``get_current_pool('Joker', rarity, ...)`` and emits the existing public
``joker_generation_pools`` record contract.  Static center identity/order comes
from the running game's ``G.P_JOKER_RARITY_POOLS``; profile/runtime eligibility
is never guessed from the Python catalogue.

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
) -> dict[int, list[dict[str, object]]] | None:
    """Return exact currently eligible Joker center records, or ``None``.

    Records preserve the running game's rarity-pool order and match the existing
    translator/state contract: ``rarity``, ``key``, ``unlocked``,
    ``no_pool_flag`` and ``yes_pool_flag``.  Centers vanilla would replace with
    ``UNAVAILABLE`` are omitted; the headless static catalogue restores their
    positions when ``eligible_keys`` are supplied to the identity RNG owner.
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

        result: dict[int, list[dict[str, object]]] = {}
        for rarity in _REQUIRED_RARITIES:
            eligible: list[dict[str, object]] = []
            for center_value in rarity_pools[rarity]:
                center = _required_table_fields(decoder, center_value)
                key = _required_string(center.get("key"))
                unlocked = _optional_boolean(center.get("unlocked"))
                no_pool_flag = _optional_string(center.get("no_pool_flag"))
                yes_pool_flag = _optional_string(center.get("yes_pool_flag"))

                if rarity != 4 and unlocked is False:
                    continue
                if _lua_truthy(used_jokers.get(key)) and not showman_present:
                    continue
                if no_pool_flag is not None and _lua_truthy(pool_flags.get(no_pool_flag)):
                    continue
                if yes_pool_flag is not None and not _lua_truthy(pool_flags.get(yes_pool_flag)):
                    continue
                if _lua_truthy(banned_keys.get(key)):
                    continue

                eligible.append(
                    {
                        "rarity": rarity,
                        "key": key,
                        "unlocked": unlocked,
                        "no_pool_flag": no_pool_flag,
                        "yes_pool_flag": yes_pool_flag,
                    }
                )

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
    if value is None or value.kind == "nil":
        return None
    if value.kind != "string":
        raise LuaJITMemoryError("optional runtime flag is not a string")
    text = str(value.value)
    if not text:
        raise LuaJITMemoryError("optional runtime flag is empty")
    return text


def _optional_boolean(value: LuaValue | None) -> bool | None:
    if value is None or value.kind == "nil":
        return None
    if value.kind != "boolean":
        raise LuaJITMemoryError("optional runtime boolean is not a boolean")
    return bool(value.value)


def _lua_truthy(value: LuaValue | None) -> bool:
    if value is None or value.kind == "nil":
        return False
    if value.kind == "boolean" and value.value is False:
        return False
    return True
