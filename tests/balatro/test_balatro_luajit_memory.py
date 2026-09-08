import struct

from games.balatro.live.external.luajit_memory import LuaJITGC64Decoder


class _MemoryReader:
    def __init__(self, base=0x100000, size=0x20000):
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


def _gc_value(decoder, pointer, tag):
    return decoder.encoded_gc_value(pointer, tag)


def _write_string(reader, address, text):
    payload = text.encode("utf-8")
    header = bytearray(24)
    header[9] = 4
    struct.pack_into("<I", header, 20, len(payload))
    reader.write(address, header + payload)


def _write_table(reader, address, node, hmask):
    header = bytearray(64)
    header[9] = 11
    struct.pack_into("<Q", header, 40, node)
    struct.pack_into("<I", header, 52, hmask)
    reader.write(address, header)


def _write_node(reader, address, value_raw, key_raw):
    reader.write(address, struct.pack("<QQQ", value_raw, key_raw, 0))


def test_gc64_value_decoding():
    reader = _MemoryReader()
    decoder = LuaJITGC64Decoder(reader)

    assert decoder.decode_value(0xFFFFFFFFFFFFFFFF).kind == "nil"
    assert decoder.decode_value(
        ((decoder.LJ_TTRUE & decoder.TAG_MASK) << 47) | decoder.POINTER_MASK
    ).value is True

    integer = ((decoder.LJ_TISNUM & decoder.TAG_MASK) << 47) | 0xFFFFFFF6
    assert decoder.decode_value(integer).value == -10

    raw_double = struct.unpack("<Q", struct.pack("<d", 12.5))[0]
    value = decoder.decode_value(raw_double)
    assert value.kind == "number"
    assert value.value == 12.5


def test_string_fields_decode_gc64_table():
    reader = _MemoryReader()
    decoder = LuaJITGC64Decoder(reader)

    key = 0x100100
    table = 0x101000
    nodes = 0x102000
    _write_string(reader, key, "STATE")
    _write_table(reader, table, nodes, 0)

    key_raw = _gc_value(decoder, key, decoder.LJ_TSTR)
    value_raw = ((decoder.LJ_TISNUM & decoder.TAG_MASK) << 47) | 7
    _write_node(reader, nodes, value_raw, key_raw)

    fields = decoder.string_fields(table)
    assert fields["STATE"].kind == "integer"
    assert fields["STATE"].value == 7


def test_discovers_balatro_g_table_from_game_key_node():
    reader = _MemoryReader()
    decoder = LuaJITGC64Decoder(reader)

    strings = {
        "GAME": 0x100100,
        "STATE": 0x100180,
        "hand": 0x100200,
        "jokers": 0x100280,
    }
    for text, address in strings.items():
        _write_string(reader, address, text)

    g_table = 0x101000
    nodes = 0x102000
    child_tables = {
        "GAME": 0x103000,
        "hand": 0x103100,
        "jokers": 0x103200,
    }
    _write_table(reader, g_table, nodes, 3)
    for child in child_tables.values():
        _write_table(reader, child, 0, 0)

    entries = [
        (
            _gc_value(decoder, child_tables["GAME"], decoder.LJ_TTAB),
            _gc_value(decoder, strings["GAME"], decoder.LJ_TSTR),
        ),
        (
            ((decoder.LJ_TISNUM & decoder.TAG_MASK) << 47) | 6,
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
