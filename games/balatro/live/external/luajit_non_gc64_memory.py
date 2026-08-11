from __future__ import annotations

import math
import struct

from .luajit_memory import LuaJITMemoryError, LuaTableMeta, LuaValue
from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader


class LuaJITNonGC64Decoder:
    """Read-only decoder for Balatro's observed LuaJIT non-GC64 layout.

    Balatro's Windows runtime exposes the older LuaJIT 2.1-era object layout:
    32-bit pseudo-pointers inside a 64-bit process, split 32/32 TValues,
    16-byte GCstr objects and 32-byte GCtab objects. The decoder is deliberately
    narrow and only traverses ordinary strings, tables, numbers and booleans.
    It never writes process memory or exposes LuaJIT PRNG state.
    """

    POINTER_MASK = 0xFFFFFFFF

    LJ_TNIL = 0xFFFFFFFF
    LJ_TFALSE = 0xFFFFFFFE
    LJ_TTRUE = 0xFFFFFFFD
    LJ_TLIGHTUD = 0xFFFFFFFC
    LJ_TSTR = 0xFFFFFFFB
    LJ_TUPVAL = 0xFFFFFFFA
    LJ_TTHREAD = 0xFFFFFFF9
    LJ_TPROTO = 0xFFFFFFF8
    LJ_TFUNC = 0xFFFFFFF7
    LJ_TTRACE = 0xFFFFFFF6
    LJ_TCDATA = 0xFFFFFFF5
    LJ_TTAB = 0xFFFFFFF4
    LJ_TUDATA = 0xFFFFFFF3
    # x64 non-GC64 LuaJIT uses a distinct integer tag.
    LJ_TISNUM = 0xFFFEFFFF

    GC_STRING_TYPE = 4
    GC_TABLE_TYPE = 11

    GCSTR_SIZE = 16
    GCTAB_SIZE = 32
    NODE_SIZE = 24

    GCSTR_GCT_OFFSET = 5
    GCSTR_LENGTH_OFFSET = 12

    GCTAB_GCT_OFFSET = 5
    GCTAB_ARRAY_OFFSET = 8
    GCTAB_NODE_OFFSET = 20
    GCTAB_ASIZE_OFFSET = 24
    GCTAB_HMASK_OFFSET = 28

    MAX_STRING_BYTES = 1024 * 1024
    MAX_TABLE_HASH_NODES = 1 << 16
    MAX_TABLE_ARRAY_SLOTS = 1 << 20

    def __init__(self, reader: WindowsProcessMemoryReader):
        self.reader = reader

    @classmethod
    def tag(cls, raw: int) -> int:
        return (raw >> 32) & 0xFFFFFFFF

    @classmethod
    def gc_pointer(cls, raw: int) -> int:
        return raw & cls.POINTER_MASK

    @classmethod
    def encoded_gc_value(cls, pointer: int, tag: int) -> int:
        return (pointer & cls.POINTER_MASK) | ((tag & 0xFFFFFFFF) << 32)

    def read_u64(self, address: int) -> int:
        data = self.reader.read(address, 8)
        if len(data) != 8:
            raise LuaJITMemoryError(f"short qword read at 0x{address:x}")
        return struct.unpack("<Q", data)[0]

    def read_value_at(self, address: int) -> LuaValue:
        return self.decode_value(self.read_u64(address))

    def decode_value(self, raw: int) -> LuaValue:
        tag = self.tag(raw)
        low = raw & 0xFFFFFFFF

        if tag == self.LJ_TNIL:
            return LuaValue("nil", None, raw)
        if tag == self.LJ_TFALSE:
            return LuaValue("boolean", False, raw)
        if tag == self.LJ_TTRUE:
            return LuaValue("boolean", True, raw)
        if tag == self.LJ_TISNUM:
            value = low
            if value & 0x80000000:
                value -= 1 << 32
            return LuaValue("integer", value, raw)
        if tag == self.LJ_TSTR:
            return LuaValue("string", self.read_string(low), raw)
        if tag == self.LJ_TTAB:
            return LuaValue("table", low, raw)
        if tag == self.LJ_TFUNC:
            return LuaValue("function", low, raw)
        if tag == self.LJ_TTHREAD:
            return LuaValue("thread", low, raw)
        if tag == self.LJ_TUDATA:
            return LuaValue("userdata", low, raw)
        if tag == self.LJ_TCDATA:
            return LuaValue("cdata", low, raw)
        if tag == self.LJ_TLIGHTUD:
            return LuaValue("lightuserdata", low, raw)

        number = struct.unpack("<d", struct.pack("<Q", raw))[0]
        if not math.isfinite(number):
            raise LuaJITMemoryError(
                f"unexpected non-finite/unknown TValue tag {tag:#x}"
            )
        return LuaValue("number", number, raw)

    def read_string(self, address: int) -> str:
        header = self.reader.read(address, self.GCSTR_SIZE)
        if len(header) != self.GCSTR_SIZE:
            raise LuaJITMemoryError(f"short GCstr header at 0x{address:x}")
        gct = header[self.GCSTR_GCT_OFFSET]
        length = struct.unpack_from("<I", header, self.GCSTR_LENGTH_OFFSET)[0]
        if gct != self.GC_STRING_TYPE:
            raise LuaJITMemoryError(
                f"object at 0x{address:x} is not a LuaJIT string (gct={gct})"
            )
        if length > self.MAX_STRING_BYTES:
            raise LuaJITMemoryError(
                f"LuaJIT string at 0x{address:x} has implausible length {length}"
            )
        payload = self.reader.read(address + self.GCSTR_SIZE, length)
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("utf-8", errors="replace")

    def read_table_meta(self, address: int) -> LuaTableMeta:
        header = self.reader.read(address, self.GCTAB_SIZE)
        if len(header) != self.GCTAB_SIZE:
            raise LuaJITMemoryError(f"short GCtab header at 0x{address:x}")
        gct = header[self.GCTAB_GCT_OFFSET]
        if gct != self.GC_TABLE_TYPE:
            raise LuaJITMemoryError(
                f"object at 0x{address:x} is not a LuaJIT table (gct={gct})"
            )

        array = struct.unpack_from("<I", header, self.GCTAB_ARRAY_OFFSET)[0]
        node = struct.unpack_from("<I", header, self.GCTAB_NODE_OFFSET)[0]
        asize = struct.unpack_from("<I", header, self.GCTAB_ASIZE_OFFSET)[0]
        hmask = struct.unpack_from("<I", header, self.GCTAB_HMASK_OFFSET)[0]

        if asize > self.MAX_TABLE_ARRAY_SLOTS:
            raise LuaJITMemoryError(
                f"table at 0x{address:x} has implausible array size {asize}"
            )
        if hmask >= self.MAX_TABLE_HASH_NODES:
            raise LuaJITMemoryError(
                f"table at 0x{address:x} has implausible hash mask {hmask}"
            )

        return LuaTableMeta(
            address=address,
            array=array,
            node=node,
            asize=asize,
            hmask=hmask,
        )

    def hash_items(
        self,
        table: int | LuaTableMeta,
    ) -> tuple[tuple[LuaValue, LuaValue], ...]:
        meta = table if isinstance(table, LuaTableMeta) else self.read_table_meta(table)
        if not meta.node:
            return ()

        result: list[tuple[LuaValue, LuaValue]] = []
        for index in range(meta.hmask + 1):
            address = meta.node + index * self.NODE_SIZE
            try:
                value = self.read_value_at(address)
                key = self.read_value_at(address + 8)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue
            if value.kind == "nil" or key.kind == "nil":
                continue
            result.append((key, value))
        return tuple(result)

    def array_items(
        self,
        table: int | LuaTableMeta,
    ) -> tuple[tuple[int, LuaValue], ...]:
        meta = table if isinstance(table, LuaTableMeta) else self.read_table_meta(table)
        if not meta.array or not meta.asize:
            return ()

        result: list[tuple[int, LuaValue]] = []
        for index in range(meta.asize):
            try:
                value = self.read_value_at(meta.array + index * 8)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue
            if value.kind != "nil":
                result.append((index, value))
        return tuple(result)

    def string_fields(self, table: int) -> dict[str, LuaValue]:
        fields: dict[str, LuaValue] = {}
        for key, value in self.hash_items(table):
            if key.kind == "string":
                fields[str(key.value)] = value
        return fields

    def find_gc_strings(
        self,
        text: str,
        *,
        max_matches: int = 256,
    ) -> tuple[int, ...]:
        """Find validated interned strings without capping on raw byte decoys."""

        encoded = text.encode("utf-8")
        result: list[int] = []
        seen_payloads: set[int] = set()
        overlap = max(0, len(encoded) - 1)

        for base, data in self.reader.iter_readable_chunks(
            chunk_size=1024 * 1024,
            overlap=overlap,
        ):
            start = 0
            while True:
                index = data.find(encoded, start)
                if index < 0:
                    break
                start = index + 1

                payload = base + index
                if payload in seen_payloads:
                    continue
                seen_payloads.add(payload)

                address = payload - self.GCSTR_SIZE
                if address <= 0:
                    continue
                try:
                    header = self.reader.read(address, self.GCSTR_SIZE)
                except BalatroProcessMemoryError:
                    continue
                if len(header) != self.GCSTR_SIZE:
                    continue
                if header[self.GCSTR_GCT_OFFSET] != self.GC_STRING_TYPE:
                    continue
                length = struct.unpack_from(
                    "<I",
                    header,
                    self.GCSTR_LENGTH_OFFSET,
                )[0]
                if length != len(encoded):
                    continue
                try:
                    if self.reader.read(payload, length) != encoded:
                        continue
                except BalatroProcessMemoryError:
                    continue

                result.append(address)
                if len(result) >= max_matches:
                    return tuple(result)

        return tuple(result)

    def find_key_nodes_for_string(self, string_address: int) -> tuple[int, ...]:
        raw = self.encoded_gc_value(string_address, self.LJ_TSTR)
        pattern = struct.pack("<Q", raw)
        references = self.reader.find_bytes(pattern, max_matches=1024)
        result: list[int] = []

        for reference in references:
            node = reference - 8
            if node <= 0:
                continue
            try:
                key = self.read_value_at(node + 8)
                value = self.read_value_at(node)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue
            if key.kind != "string" or key.raw != raw or value.kind == "nil":
                continue
            result.append(node)

        return tuple(dict.fromkeys(result))

    def find_table_owners_of_node(
        self,
        node_address: int,
        *,
        max_index: int = 4096,
    ) -> tuple[int, ...]:
        """Find non-GC64 GCtab objects whose hash array contains a node."""

        possible: dict[int, int] = {
            node_address - index * self.NODE_SIZE: index
            for index in range(max_index + 1)
            if 0 < node_address - index * self.NODE_SIZE <= self.POINTER_MASK
        }
        if not possible:
            return ()

        result: list[int] = []
        seen: set[int] = set()
        for base, data in self.reader.iter_readable_chunks(
            chunk_size=1024 * 1024,
            overlap=3,
        ):
            start = (-base) % 4
            for offset in range(start, len(data) - 3, 4):
                pointer = struct.unpack_from("<I", data, offset)[0]
                index = possible.get(pointer)
                if index is None:
                    continue

                pointer_address = base + offset
                table_address = pointer_address - self.GCTAB_NODE_OFFSET
                if table_address <= 0 or table_address in seen:
                    continue
                try:
                    meta = self.read_table_meta(table_address)
                except (BalatroProcessMemoryError, LuaJITMemoryError):
                    continue
                if meta.node != pointer or index > meta.hmask:
                    continue
                if meta.node + index * self.NODE_SIZE != node_address:
                    continue

                seen.add(table_address)
                result.append(table_address)

        return tuple(result)

    def discover_balatro_g_table(self) -> int:
        required = {"GAME", "STATE", "hand", "jokers"}
        candidates: list[int] = []

        for string_address in self.find_gc_strings("GAME", max_matches=64):
            for node in self.find_key_nodes_for_string(string_address):
                try:
                    value = self.read_value_at(node)
                except (BalatroProcessMemoryError, LuaJITMemoryError):
                    continue
                if value.kind != "table":
                    continue

                for owner in self.find_table_owners_of_node(node):
                    try:
                        keys = set(self.string_fields(owner))
                    except (BalatroProcessMemoryError, LuaJITMemoryError):
                        continue
                    if required.issubset(keys):
                        candidates.append(owner)

        unique = tuple(dict.fromkeys(candidates))
        if len(unique) != 1:
            raise LuaJITMemoryError(
                "unable to identify one Balatro G table from live non-GC64 memory; "
                f"validated candidates={len(unique)}"
            )
        return unique[0]
