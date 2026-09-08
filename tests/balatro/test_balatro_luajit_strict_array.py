import struct

import pytest

from games.balatro.live.external.luajit_memory import LuaJITMemoryError
from games.balatro.live.external.luajit_non_gc64_memory import LuaJITNonGC64Decoder


class _MemoryReader:
    def __init__(self, base=0x100000, size=0x40000):
        self.base = base
        self.data = bytearray(size)

    def write(self, address, data):
        offset = address - self.base
        self.data[offset : offset + len(data)] = data

    def read(self, address, size):
        offset = address - self.base
        if offset < 0 or offset + size > len(self.data):
            raise RuntimeError("out of fake memory")
        return bytes(self.data[offset : offset + size])


def _write_table(reader, address, *, array, asize):
    header = bytearray(32)
    header[5] = LuaJITNonGC64Decoder.GC_TABLE_TYPE
    struct.pack_into("<I", header, 8, array)
    struct.pack_into("<I", header, 24, asize)
    reader.write(address, header)


def _integer_value(decoder, value):
    return ((decoder.LJ_TISNUM & 0xFFFFFFFF) << 32) | (value & 0xFFFFFFFF)


def test_balatro_env_r1_strict_array_decode_rejects_unreadable_tvalue_instead_of_shrinking():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)
    table = 0x102000
    array = 0x103000
    _write_table(reader, table, array=array, asize=3)

    invalid_nan_tvalue = 0x7FF8000000000000
    reader.write(
        array,
        b"".join(
            (
                struct.pack("<Q", _integer_value(decoder, 1)),
                struct.pack("<Q", invalid_nan_tvalue),
                struct.pack("<Q", _integer_value(decoder, 3)),
            )
        ),
    )

    # The existing tolerant path remains available for non-authoritative UI/state
    # reads and demonstrates the exact failure mode this R1 guard is preventing.
    assert [value.value for _, value in decoder.array_items(table)] == [1, 3]

    with pytest.raises(LuaJITMemoryError, match="unexpected non-finite/unknown TValue"):
        decoder.array_items_strict(table)


def test_balatro_env_r1_strict_array_decode_preserves_valid_and_nil_slots():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)
    table = 0x102000
    array = 0x103000
    _write_table(reader, table, array=array, asize=3)

    nil_tvalue = (decoder.LJ_TNIL & 0xFFFFFFFF) << 32
    reader.write(
        array,
        b"".join(
            (
                struct.pack("<Q", _integer_value(decoder, 1)),
                struct.pack("<Q", nil_tvalue),
                struct.pack("<Q", _integer_value(decoder, 3)),
            )
        ),
    )

    items = decoder.array_items_strict(table)
    assert [(index, value.value) for index, value in items] == [(0, 1), (2, 3)]
