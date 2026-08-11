from __future__ import annotations

import argparse

from .luajit_memory import LuaJITGC64Decoder, LuaJITMemoryError, LuaValue
from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader


ROOT_FIELDS = (
    "GAME",
    "STATE",
    "STATE_COMPLETE",
    "STATES",
    "hand",
    "jokers",
    "consumeables",
    "deck",
    "shop_jokers",
    "shop_booster",
    "shop_vouchers",
)


def _value_text(value: LuaValue | None) -> str:
    if value is None:
        return "missing"
    if value.kind == "table":
        return f"table@0x{int(value.value):x}"
    return f"{value.kind}:{value.value}"


def _table_keys(decoder: LuaJITGC64Decoder, address: int, limit: int = 80) -> str:
    fields = decoder.string_fields(address)
    keys = sorted(fields)
    suffix = "" if len(keys) <= limit else f" ... (+{len(keys) - limit})"
    return ", ".join(keys[:limit]) + suffix


def _area_count(decoder: LuaJITGC64Decoder, value: LuaValue | None) -> int | None:
    if value is None or value.kind != "table":
        return None
    fields = decoder.string_fields(int(value.value))
    cards = fields.get("cards")
    if cards is None or cards.kind != "table":
        return None
    array = decoder.array_items(int(cards.value))
    # Balatro/Lua arrays are 1-based. Ignore a non-nil zero slot if a future
    # runtime ever uses one; this is diagnostics only and not planner state yet.
    return sum(1 for index, _ in array if index >= 1)


def _state_name(decoder: LuaJITGC64Decoder, root: dict[str, LuaValue]) -> str | None:
    state = root.get("STATE")
    states = root.get("STATES")
    if state is None or states is None or states.kind != "table":
        return None
    if state.kind not in {"integer", "number"}:
        return None
    target = int(state.value)
    for name, value in decoder.string_fields(int(states.value)).items():
        if value.kind in {"integer", "number"} and int(value.value) == target:
            return name
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read Balatro's current LuaJIT heap directly through Win32 "
            "ReadProcessMemory and probe the live G table. No injection, writes, "
            "save parsing, or third-party runtime is used."
        )
    )
    parser.parse_args()

    try:
        with WindowsProcessMemoryReader.from_balatro_window() as reader:
            decoder = LuaJITGC64Decoder(reader)
            print(f"Balatro PID -> {reader.pid}")
            print("Observation source -> live Balatro process memory")
            print("External runtime dependency -> none")
            print("Process writes/injection -> False")
            print("save.jkr used -> False")
            print("Hidden RNG requested -> False")
            print("Discovering Balatro G table -> ...")
            g_table = decoder.discover_balatro_g_table()
            root = decoder.string_fields(g_table)

            print(f"Balatro G table -> 0x{g_table:x}")
            print("G discovery -> PASS")
            print(f"G string fields -> {len(root)}")
            state_name = _state_name(decoder, root)
            if state_name is not None:
                print(f"Live phase -> {state_name}")

            for name in ROOT_FIELDS:
                value = root.get(name)
                print(f"G.{name} -> {_value_text(value)}")

            for name in ("GAME", "hand", "jokers", "consumeables", "deck"):
                value = root.get(name)
                if value is None or value.kind != "table":
                    continue
                address = int(value.value)
                print(f"{name} keys -> {_table_keys(decoder, address)}")
                count = _area_count(decoder, value)
                if count is not None:
                    print(f"{name} live card count -> {count}")

            print("Live-memory probe -> PASS")
            return 0
    except (BalatroProcessMemoryError, LuaJITMemoryError, OSError) as error:
        print("Live-memory probe -> FAIL")
        print(f"Reason -> {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
