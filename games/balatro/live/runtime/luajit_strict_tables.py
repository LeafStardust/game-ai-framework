"""All-or-nothing LuaJIT hash-table reads for authoritative live state.

The ordinary decoder deliberately tolerates unreadable hash nodes so UI-facing
observation can survive transient process-memory races.  That behaviour is not
safe for mechanics-critical maps such as ``G.GAME.used_jokers``,
``G.GAME.pool_flags`` and ``G.GAME.banned_keys``: silently dropping one entry
can change Joker eligibility.

This module provides a narrow strict path without changing the tolerant decoder
contract used elsewhere.
"""

from __future__ import annotations

import struct

from .luajit_memory import LuaTableMeta, LuaValue, LuaJITMemoryError
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder
from .process_memory import BalatroProcessMemoryError


def hash_items_strict(
    decoder: LuaJITNonGC64Decoder,
    table: int | LuaTableMeta,
) -> tuple[tuple[LuaValue, LuaValue], ...]:
    """Decode every LuaJIT hash node or fail the entire authoritative read.

    Nil nodes remain ordinary empty hash slots.  Any structural memory failure,
    short node block, or TValue decode failure propagates instead of silently
    shrinking the mapping.
    """

    meta = table if isinstance(table, LuaTableMeta) else decoder.read_table_meta(table)
    if not meta.node:
        return ()

    count = meta.hmask + 1
    try:
        block = decoder.reader.read(meta.node, count * decoder.NODE_SIZE)
    except BalatroProcessMemoryError:
        raise
    if len(block) != count * decoder.NODE_SIZE:
        raise LuaJITMemoryError(
            f"short LuaJIT hash-node block at 0x{meta.node:x}"
        )

    result: list[tuple[LuaValue, LuaValue]] = []
    for index in range(count):
        offset = index * decoder.NODE_SIZE
        value_raw, key_raw = struct.unpack_from("<QQ", block, offset)
        value = decoder.decode_value(value_raw)
        key = decoder.decode_value(key_raw)
        if value.kind == "nil" or key.kind == "nil":
            continue
        result.append((key, value))
    return tuple(result)


def string_fields_strict(
    decoder: LuaJITNonGC64Decoder,
    table: int | LuaTableMeta,
) -> dict[str, LuaValue]:
    """Return a complete string-keyed view of an authoritative Lua table.

    Non-string keys are ignored exactly as with the tolerant ``string_fields``
    helper, but no unreadable hash node may disappear silently.
    """

    fields: dict[str, LuaValue] = {}
    for key, value in hash_items_strict(decoder, table):
        if key.kind == "string":
            fields[str(key.value)] = value
    return fields
