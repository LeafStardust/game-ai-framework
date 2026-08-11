import struct

from games.balatro.live.external.luajit_non_gc64_memory import (
    LuaJITNonGC64Decoder,
)


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

    def find_bytes(self, needle, *, max_matches=256, chunk_size=1024 * 1024):
        result = []
        start = 0
        raw = bytes(self.data)
        while len(result) < max_matches:
            index = raw.find(needle, start)
            if index < 0:
                break
            result.append(self.base + index)
            start = index + 1
        return tuple(result)

    def iter_readable_chunks(self, *, chunk_size=1024 * 1024, overlap=0):
        yield self.base, bytes(self.data)


def _write_string(reader, address, text):
    payload = text.encode("utf-8")
    header = bytearray(16)
    struct.pack_into("<I", header, 0, 0x00123450)
    header[4] = 1
    header[5] = 4
    header[6] = 0
    header[7] = 0
    struct.pack_into("<I", header, 8, 0x2977AA7E)
    struct.pack_into("<I", header, 12, len(payload))
    reader.write(address, header + payload)


def _write_table(reader, address, node=0, hmask=0, array=0, asize=0):
    header = bytearray(32)
    struct.pack_into("<I", header, 0, 0x00124440)
    header[4] = 1
    header[5] = 11
    header[6] = 0
    header[7] = 0
    struct.pack_into("<I", header, 8, array)
    struct.pack_into("<I", header, 20, node)
    struct.pack_into("<I", header, 24, asize)
    struct.pack_into("<I", header, 28, hmask)
    reader.write(address, header)


def _write_node(reader, address, value_raw, key_raw):
    reader.write(address, struct.pack("<QQII", value_raw, key_raw, 0, 0))


def _gc_value(decoder, pointer, tag):
    return decoder.encoded_gc_value(pointer, tag)


def _integer_value(decoder, value):
    return ((decoder.LJ_TISNUM & 0xFFFFFFFF) << 32) | (value & 0xFFFFFFFF)


def test_observed_balatro_string_header_decodes():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)
    address = 0x101000

    _write_string(reader, address, "GAME")

    assert decoder.GCSTR_SIZE == 16
    assert decoder.read_string(address) == "GAME"
    assert decoder.find_gc_strings("GAME") == (address,)


def test_non_gc64_tvalue_decoding():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)
    string_address = 0x101000
    table_address = 0x102000
    _write_string(reader, string_address, "STATE")
    _write_table(reader, table_address)

    assert decoder.decode_value(_integer_value(decoder, -10)).value == -10
    assert decoder.decode_value(
        _gc_value(decoder, string_address, decoder.LJ_TSTR)
    ).value == "STATE"
    assert decoder.decode_value(
        _gc_value(decoder, table_address, decoder.LJ_TTAB)
    ).value == table_address

    raw_double = struct.unpack("<Q", struct.pack("<d", 12.5))[0]
    value = decoder.decode_value(raw_double)
    assert value.kind == "number"
    assert value.value == 12.5


def test_non_gc64_string_fields_decode_table():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)

    key = 0x101000
    table = 0x102000
    nodes = 0x103000
    _write_string(reader, key, "STATE")
    _write_table(reader, table, node=nodes, hmask=0)
    _write_node(
        reader,
        nodes,
        _integer_value(decoder, 7),
        _gc_value(decoder, key, decoder.LJ_TSTR),
    )

    fields = decoder.string_fields(table)
    assert fields["STATE"].kind == "integer"
    assert fields["STATE"].value == 7


def test_discovers_balatro_g_table_with_non_gc64_layout():
    reader = _MemoryReader()
    decoder = LuaJITNonGC64Decoder(reader)

    strings = {
        "GAME": 0x101000,
        "STATE": 0x101100,
        "hand": 0x101200,
        "jokers": 0x101300,
    }
    for text, address in strings.items():
        _write_string(reader, address, text)

    g_table = 0x102000
    nodes = 0x103000
    child_tables = {
        "GAME": 0x104000,
        "hand": 0x104100,
        "jokers": 0x104200,
    }

    _write_table(reader, g_table, node=nodes, hmask=3)
    for child in child_tables.values():
        _write_table(reader, child)

    entries = [
        (
            _gc_value(decoder, child_tables["GAME"], decoder.LJ_TTAB),
            _gc_value(decoder, strings["GAME"], decoder.LJ_TSTR),
        ),
        (
            _integer_value(decoder, 6),
            _gc_value(decoder, strings["STATE"], decoder.LJ_TSTR),
        ),
        (
            _gc_value(decoder, child_tables["hand"], decoder.LJ_TTAB),
            _gc_value(decoder, strings["hand"], decoder.LJ_TSTR),
        ),
        (
            _gc_value(decoder, child_tables["jokers"], decoder.LJ_TTAB),
            _gc_value(decoder, strings["jokers"], decoder.LJ_TSTR),
        ),
    ]

    for index, (value_raw, key_raw) in enumerate(entries):
        _write_node(reader, nodes + index * decoder.NODE_SIZE, value_raw, key_raw)

    assert decoder.discover_balatro_g_table() == g_table
