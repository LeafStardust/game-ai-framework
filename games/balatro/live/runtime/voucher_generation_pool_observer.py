"""Authoritative live producer for normal Voucher-generation eligibility.

Mirrors the Voucher branch of pinned vanilla ``get_current_pool('Voucher')``.
Unlike the Joker/Tarot/Planet public catalogues, this observer preserves every
runtime Voucher-pool position and attaches an explicit ``eligible`` bit. Vanilla
identity selection samples this source-length pool with ``UNAVAILABLE`` sentinels
before keyed resampling, so filtering ineligible entries would change RNG.

All mechanics-critical reads are all-or-nothing. ``None`` means Voucher
eligibility is unobserved and headless generation must fail closed.
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


def observe_voucher_generation_pool(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
) -> list[dict[str, object]] | None:
    """Return the exact ordered runtime Voucher catalogue, or ``None``."""
    try:
        game = _required_table_fields(decoder, root.get("GAME"))
        used_vouchers = _required_table_fields(decoder, game.get("used_vouchers"))
        used_jokers = _required_table_fields(decoder, game.get("used_jokers"))
        pool_flags = _required_table_fields(decoder, game.get("pool_flags"))
        banned_keys = _required_table_fields(decoder, game.get("banned_keys"))
        showman_present = _observe_showman_present(decoder, root.get("jokers"))
        current_shop = _observe_current_shop_voucher_keys(decoder, root.get("shop_vouchers"))
        centers = _read_voucher_centers(decoder, root.get("P_CENTER_POOLS"))

        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for center_value in centers:
            center = _required_table_fields(decoder, center_value)
            key = _required_string(center.get("key"))
            if not key.startswith("v_") or key in seen:
                raise LuaJITMemoryError("Voucher pool contains an invalid or duplicate key")
            seen.add(key)

            cost = _required_nonnegative_integer(center.get("cost"), "Voucher center cost")
            unlocked = _optional_boolean(center.get("unlocked"))
            no_pool_flag = _optional_string(center.get("no_pool_flag"))
            yes_pool_flag = _optional_string(center.get("yes_pool_flag"))
            requires = _optional_string_array(decoder, center.get("requires"))

            eligible = unlocked is not False
            if eligible and _lua_truthy(used_jokers.get(key)) and not showman_present:
                eligible = False
            if eligible and _lua_truthy(used_vouchers.get(key)):
                eligible = False
            if eligible and any(not _lua_truthy(used_vouchers.get(required)) for required in requires):
                eligible = False
            if eligible and key in current_shop:
                eligible = False
            if no_pool_flag is not None and _lua_truthy(pool_flags.get(no_pool_flag)):
                eligible = False
            if yes_pool_flag is not None and not _lua_truthy(pool_flags.get(yes_pool_flag)):
                eligible = False
            if _lua_truthy(banned_keys.get(key)):
                eligible = False

            result.append(
                {
                    "key": key,
                    "cost": cost,
                    "unlocked": unlocked,
                    "requires": list(requires),
                    "no_pool_flag": no_pool_flag,
                    "yes_pool_flag": yes_pool_flag,
                    "eligible": bool(eligible),
                }
            )
        return result
    except (BalatroProcessMemoryError, LuaJITMemoryError, KeyError, TypeError, ValueError):
        return None


def _read_voucher_centers(
    decoder: LuaJITNonGC64Decoder,
    pools_value: LuaValue | None,
) -> list[LuaValue]:
    pools = _required_table_fields(decoder, pools_value)
    value = pools.get("Voucher")
    if value is None or value.kind != "table":
        raise LuaJITMemoryError("G.P_CENTER_POOLS.Voucher is unavailable")
    centers: list[LuaValue] = []
    for _, item in decoder.array_items_strict(int(value.value)):
        if item.kind != "table":
            raise LuaJITMemoryError("Voucher generation pool contains a non-table center")
        centers.append(item)
    if not centers:
        raise LuaJITMemoryError("Voucher generation pool is empty")
    return centers


def _optional_string_array(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> tuple[str, ...]:
    if value is None or value.kind == "nil":
        return ()
    if value.kind != "table":
        raise LuaJITMemoryError("Voucher requires is not a Lua array")
    result: list[str] = []
    for _, item in decoder.array_items_strict(int(value.value)):
        required = _required_string(item)
        if required in result:
            raise LuaJITMemoryError("Voucher requires contains a duplicate key")
        result.append(required)
    return tuple(result)


def _observe_current_shop_voucher_keys(
    decoder: LuaJITNonGC64Decoder,
    area_value: LuaValue | None,
) -> set[str]:
    # Vanilla checks ``G.shop_vouchers and G.shop_vouchers.cards``. A genuinely
    # absent area/cards table therefore means no current-shop exclusions.
    if area_value is None or area_value.kind == "nil":
        return set()
    if area_value.kind != "table":
        raise LuaJITMemoryError("G.shop_vouchers is not a Lua table")
    area = _required_table_fields(decoder, area_value)
    cards_value = area.get("cards")
    if cards_value is None or cards_value.kind == "nil":
        return set()
    if cards_value.kind != "table":
        raise LuaJITMemoryError("G.shop_vouchers.cards is not a Lua table")

    result: set[str] = set()
    for _, card_value in decoder.array_items_strict(int(cards_value.value)):
        card = _required_table_fields(decoder, card_value)
        config = _required_table_fields(decoder, card.get("config"))
        center = _required_table_fields(decoder, config.get("center"))
        key = _required_string(center.get("key"))
        if key in result:
            raise LuaJITMemoryError("G.shop_vouchers contains a duplicate Voucher key")
        result.add(key)
    return result
