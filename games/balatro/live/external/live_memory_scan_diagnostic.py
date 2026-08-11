from __future__ import annotations

import struct

from .luajit_memory import LuaJITGC64Decoder, LuaJITMemoryError
from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader


REQUIRED_G_KEYS = {"GAME", "STATE", "hand", "jokers"}


def _find_valid_gc_strings(
    decoder: LuaJITGC64Decoder,
    text: str,
    *,
    max_valid_matches: int = 64,
) -> tuple[int, ...]:
    """Find validated GCstr objects without truncating on raw byte decoys."""

    encoded = text.encode("utf-8")
    result: list[int] = []
    seen_payloads: set[int] = set()
    overlap = max(0, len(encoded) - 1)

    for base, data in decoder.reader.iter_readable_chunks(
        chunk_size=1024 * 1024,
        overlap=overlap,
    ):
        start = 0
        while True:
            index = data.find(encoded, start)
            if index < 0:
                break

            payload = base + index
            start = index + 1
            if payload in seen_payloads:
                continue
            seen_payloads.add(payload)

            address = payload - decoder.GCSTR_SIZE
            if address <= 0:
                continue

            try:
                header = decoder.reader.read(address, decoder.GCSTR_SIZE)
            except BalatroProcessMemoryError:
                continue

            if len(header) != decoder.GCSTR_SIZE:
                continue
            if header[9] != decoder.GC_STRING_TYPE:
                continue

            length = struct.unpack_from("<I", header, 20)[0]
            if length != len(encoded):
                continue

            try:
                if decoder.reader.read(payload, length) != encoded:
                    continue
            except BalatroProcessMemoryError:
                continue

            result.append(address)
            if len(result) >= max_valid_matches:
                return tuple(result)

    return tuple(result)


def main() -> int:
    try:
        with WindowsProcessMemoryReader.from_balatro_window() as reader:
            decoder = LuaJITGC64Decoder(reader)

            print(f"Balatro PID -> {reader.pid}")
            print("Diagnostic mode -> read-only live process memory")
            print("Process writes/injection -> False")
            print("save.jkr used -> False")
            print("LuaJIT ABI under test -> GC64")

            raw_game = reader.find_bytes(b"GAME", max_matches=4096)
            capped = len(raw_game) == 4096
            print(
                "Raw ASCII 'GAME' matches -> "
                f"{len(raw_game)}" + (" (capped at 4096)" if capped else "")
            )

            old_gc_strings = decoder.find_gc_strings("GAME", max_matches=128)
            valid_gc_strings = _find_valid_gc_strings(
                decoder,
                "GAME",
                max_valid_matches=64,
            )
            print(f"Old bounded GCstr matches -> {len(old_gc_strings)}")
            print(f"Validated GC64 GCstr matches -> {len(valid_gc_strings)}")

            total_nodes = 0
            owner_candidates: set[int] = set()
            best_overlap = 0
            best_owner: int | None = None
            best_keys: tuple[str, ...] = ()

            for string_address in valid_gc_strings:
                nodes = decoder.find_key_nodes_for_string(string_address)
                total_nodes += len(nodes)
                for node in nodes:
                    for owner in decoder.find_table_owners_of_node(
                        node,
                        max_index=4096,
                    ):
                        owner_candidates.add(owner)
                        try:
                            keys = tuple(sorted(decoder.string_fields(owner)))
                        except (BalatroProcessMemoryError, LuaJITMemoryError):
                            continue
                        overlap_count = len(REQUIRED_G_KEYS.intersection(keys))
                        if overlap_count > best_overlap:
                            best_overlap = overlap_count
                            best_owner = owner
                            best_keys = keys

            print(f"Encoded GAME key-node references -> {total_nodes}")
            print(f"Owning table candidates -> {len(owner_candidates)}")
            print(
                "Best required-key overlap -> "
                f"{best_overlap}/{len(REQUIRED_G_KEYS)}"
            )

            if best_owner is not None:
                preview = ", ".join(best_keys[:80])
                suffix = "" if len(best_keys) <= 80 else f" ... (+{len(best_keys) - 80})"
                print(f"Best owner -> 0x{best_owner:x}")
                print(f"Best owner keys -> {preview}{suffix}")

            exact_candidates: list[int] = []
            for owner in owner_candidates:
                try:
                    keys = set(decoder.string_fields(owner))
                except (BalatroProcessMemoryError, LuaJITMemoryError):
                    continue
                if REQUIRED_G_KEYS.issubset(keys):
                    exact_candidates.append(owner)

            exact_candidates = list(dict.fromkeys(exact_candidates))
            print(f"Validated G candidates -> {len(exact_candidates)}")
            for candidate in exact_candidates[:8]:
                print(f"Candidate G -> 0x{candidate:x}")

            if len(exact_candidates) == 1:
                print("Discovery diagnostic -> PASS")
                print("Likely failure class -> raw-match truncation in find_gc_strings")
                return 0

            print("Discovery diagnostic -> INCONCLUSIVE")
            if not valid_gc_strings:
                print("Likely failure class -> GC64 string/header assumption or scan coverage")
            elif not total_nodes:
                print("Likely failure class -> GC64 TValue encoding/reference assumption")
            elif not owner_candidates:
                print("Likely failure class -> GCtab ownership/layout assumption")
            else:
                print("Likely failure class -> G-key validation/discovery heuristic")
            return 2

    except (BalatroProcessMemoryError, LuaJITMemoryError, OSError) as error:
        print("Discovery diagnostic -> FAIL")
        print(f"Reason -> {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
