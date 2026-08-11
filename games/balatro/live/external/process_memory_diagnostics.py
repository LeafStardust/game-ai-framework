from __future__ import annotations

import argparse

from .process_memory import BalatroProcessMemoryError, WindowsProcessMemoryReader


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Attach read-only to the running Balatro process and report readable "
            "memory-region metadata. No process memory is modified."
        )
    )
    parser.parse_args()

    try:
        with WindowsProcessMemoryReader.from_balatro_window() as reader:
            regions = reader.readable_regions()
            total = sum(region.size for region in regions)
            print(f"Balatro PID -> {reader.pid}")
            print("Access mode -> read-only Win32 process memory")
            print("External runtime dependency -> none")
            print("Remote writes/injection -> False")
            print(f"Readable regions -> {len(regions)}")
            print(f"Readable bytes -> {total}")
            if regions:
                print(
                    "First readable region -> "
                    f"0x{regions[0].base:x}-0x{regions[0].end:x}"
                )
            print("Process attachment -> PASS")
            return 0
    except (BalatroProcessMemoryError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
