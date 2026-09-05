import struct

import pytest

from games.balatro.live.runtime.luajit_memory import LuaTableMeta
from games.balatro.live.runtime.luajit_non_gc64_memory import LuaJITNonGC64Decoder
from games.balatro.live.runtime.luajit_strict_tables import hash_items_strict
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError


class _Reader:
    def __init__(self, blocks: dict[int, bytes]):
        self.blocks = dict(blocks)

    def read(self, address: int, size: int) -> bytes:
        payload = self.blocks.get(address)
        if payload is None:
            raise BalatroProcessMemoryError(f"unreadable 0x{address:x}")
        return payload[:size]


def _one_node_meta(node: int = 0x1000) -> LuaTableMeta:
    return LuaTableMeta(address=0x500, array=0, node=node, asize=0, hmask=0)


def test_env_r2_tolerant_hash_read_can_skip_an_unreadable_string_key():
    decoder = LuaJITNonGC64Decoder(_Reader({
        0x1000: struct.pack(
            "<QQQ",
            decoder_raw_true := (LuaJITNonGC64Decoder.LJ_TTRUE << 32),
            LuaJITNonGC64Decoder.encoded_gc_value(
                0x9000,
                LuaJITNonGC64Decoder.LJ_TSTR,
            ),
            0,
        )
    }))

    assert decoder.hash_items(_one_node_meta()) == ()
    assert decoder_raw_true != 0


def test_env_r2_strict_hash_read_rejects_the_same_unreadable_string_key():
    decoder = LuaJITNonGC64Decoder(_Reader({
        0x1000: struct.pack(
            "<QQQ",
            LuaJITNonGC64Decoder.LJ_TTRUE << 32,
            LuaJITNonGC64Decoder.encoded_gc_value(
                0x9000,
                LuaJITNonGC64Decoder.LJ_TSTR,
            ),
            0,
        )
    }))

    with pytest.raises(BalatroProcessMemoryError, match="unreadable"):
        hash_items_strict(decoder, _one_node_meta())


def test_env_r2_strict_hash_read_rejects_short_node_blocks():
    decoder = LuaJITNonGC64Decoder(_Reader({0x1000: b"\x00" * 8}))

    with pytest.raises(RuntimeError, match="short LuaJIT hash-node block"):
        hash_items_strict(decoder, _one_node_meta())
