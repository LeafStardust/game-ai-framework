from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Any

from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader


class LuaJITMemoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class LuaValue:
    kind: str
    value: Any
    raw: int


@dataclass(frozen=True)
class LuaTableMeta:
    address: int
    array: int
    node: int
    asize: int
    hmask: int


class LuaJITGC64Decoder:
    """Minimal read-only LuaJIT 2.1 GC64 heap decoder.

    The decoder implements only the ABI pieces required to traverse ordinary Lua
    strings/tables/numbers/booleans. It never calls into the remote VM and never
    reads LuaJIT's PRNG state. Layout constants are kept explicit so a Balatro or
    LÖVE runtime update fails closed instead of silently producing guessed state.
    """

    POINTER_MASK = (1 << 47) - 1
    TAG_MASK = (1 << 17) - 1

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
    LJ_TISNUM = 0xFFFFFFF2

    GC_STRING_TYPE = 4
    GC_TABLE_TYPE = 11

    GCSTR_SIZE = 24
    GCTAB_SIZE = 64
    NODE_SIZE = 24

    MAX_STRING_BYTES = 1024 * 1024
    MAX_TABLE_HASH_NODES = 1 << 16
    MAX_TABLE_ARRAY_SLOTS = 1 << 20

    def __init__(self, reader: WindowsProcessMemoryReader):
        self.reader = reader

    @staticmethod
    def _signed64(raw: int) -> int:
        return raw if raw < (1 << 63) else raw - (1 << 64)

    @classmethod
    def tag(cls, raw: int) -> int:
        return (cls._signed64(raw) >> 47) & 0xFFFFFFFF

    @classmethod
    def gc_pointer(cls, raw: int) -> int:
        return raw & cls.POINTER_MASK

    @classmethod
    def encoded_gc_value(cls, pointer: int, tag: int) -> int:
        return (pointer & cls.POINTER_MASK) | ((tag & cls.TAG_MASK) << 47)

    def read_u64(self, address: int) -> int:
        data = self.reader.read(address, 8)
        if len(data) != 8:
            raise LuaJITMemoryError(f"short qword read at 0x{address:x}")
        return struct.unpack("<Q", data)[0]

    def read_value_at(self, address: int) -> LuaValue:
        return self.decode_value(self.read_u64(address))

    def decode_value(self, raw: int) -> LuaValue:
        # LuaJIT GC64 uses NaN-tagging. Ordinary IEEE-754 doubles do not have all
        # upper 13 bits set; special values do.
        if raw >> 51 != 0x1FFF:
            number = struct.unpack("<d", struct.pack("<Q", raw))[0]
            if not math.isfinite(number):
                raise LuaJITMemoryError("unexpected non-finite untagged Lua number")
            return LuaValue("number", number, raw)

        tag = self.tag(raw)
        if tag == self.LJ_TNIL:
            return LuaValue("nil", None, raw)
        if tag == self.LJ_TFALSE:
            return LuaValue("boolean", False, raw)
        if tag == self.LJ_TTRUE:
            return LuaValue("boolean", True, raw)
        if tag == self.LJ_TISNUM:
            value = raw & 0xFFFFFFFF
            if value & 0x80000000:
                value -= 1 << 32
            return LuaValue("integer", value, raw)
        if tag == self.LJ_TSTR:
            pointer = self.gc_pointer(raw)
            return LuaValue("string", self.read_string(pointer), raw)
        if tag == self.LJ_TTAB:
            return LuaValue("table", self.gc_pointer(raw), raw)
        if tag == self.LJ_TFUNC:
            return LuaValue("function", self.gc_pointer(raw), raw)
        if tag == self.LJ_TTHREAD:
            return LuaValue("thread", self.gc_pointer(raw), raw)
        if tag == self.LJ_TUDATA:
            return LuaValue("userdata", self.gc_pointer(raw), raw)
        if tag == self.LJ_TCDATA:
            return LuaValue("cdata", self.gc_pointer(raw), raw)
        if tag == self.LJ_TLIGHTUD:
            return LuaValue("lightuserdata", raw & self.POINTER_MASK, raw)
        return LuaValue(f"tag:{tag:#x}", raw & self.POINTER_MASK, raw)

    def read_string(self, address: int) -> str:
        header = self.reader.read(address, self.GCSTR_SIZE)
        if len(header) != self.GCSTR_SIZE:
            raise LuaJITMemoryError(f"short GCstr header at 0x{address:x}")
        gct = header[9]
        length = struct.unpack_from("<I", header, 20)[0]
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
        gct = header[9]
        if gct != self.GC_TABLE_TYPE:
            raise LuaJITMemoryError(
                f"object at 0x{address:x} is not a LuaJIT table (gct={gct})"
            )
        array = struct.unpack_from("<Q", header, 16)[0]
        node = struct.unpack_from("<Q", header, 40)[0]
        asize = struct.unpack_from("<I", header, 48)[0]
        hmask = struct.unpack_from("<I", header, 52)[0]
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

    def hash_items(self, table: int | LuaTableMeta) -> tuple[tuple[LuaValue, LuaValue], ...]:
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

    def array_items(self, table: int | LuaTableMeta) -> tuple[tuple[int, LuaValue], ...]:
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
        encoded = text.encode("utf-8")
        payloads = self.reader.find_bytes(encoded, max_matches=max_matches)
        result: list[int] = []
        seen: set[int] = set()
        for payload in payloads:
            address = payload - self.GCSTR_SIZE
            if address < 0:
                continue
            try:
                header = self.reader.read(address, self.GCSTR_SIZE)
            except BalatroProcessMemoryError:
                continue
            if len(header) != self.GCSTR_SIZE or header[9] != self.GC_STRING_TYPE:
                continue
            length = struct.unpack_from("<I", header, 20)[0]
            if length != len(encoded):
                continue
            try:
                if self.reader.read(payload, length) != encoded:
                    continue
            except BalatroProcessMemoryError:
                continue
            if address not in seen:
                seen.add(address)
                result.append(address)
        return tuple(result)

    def find_key_nodes_for_string(self, string_address: int) -> tuple[int, ...]:
        raw = self.encoded_gc_value(string_address, self.LJ_TSTR)
        pattern = struct.pack("<Q", raw)
        references = self.reader.find_bytes(pattern, max_matches=1024)
        result: list[int] = []
        for reference in references:
            node = reference - 8
            if node < 0:
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
        max_index: int = 1024,
    ) -> tuple[int, ...]:
        """Find GCtab objects whose hash array contains ``node_address``.

        A hash node is 24 bytes. We derive possible hash-array bases for bounded
        node indices, then scan readable memory once for those base pointers. Any
        candidate is verified as a GCtab whose node pointer and hmask encompass the
        target node.
        """

        possible: dict[int, int] = {
            node_address - index * self.NODE_SIZE: index
            for index in range(max_index + 1)
            if node_address - index * self.NODE_SIZE > 0
        }
        if not possible:
            return ()

        result: list[int] = []
        seen: set[int] = set()
        for base, data in self.reader.iter_readable_chunks(chunk_size=1024 * 1024, overlap=7):
            start = (-base) % 8
            for offset in range(start, len(data) - 7, 8):
                pointer = struct.unpack_from("<Q", data, offset)[0]
                index = possible.get(pointer)
                if index is None:
                    continue
                pointer_address = base + offset
                table_address = pointer_address - 40
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
        for string_address in self.find_gc_strings("GAME", max_matches=128):
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
                "unable to identify one Balatro G table from live memory; "
                f"validated candidates={len(unique)}"
            )
        return unique[0]
