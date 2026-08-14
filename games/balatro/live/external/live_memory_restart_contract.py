from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from games.balatro.live.injected.install import _fused_archive
from games.balatro.setup.installer import BalatroSetup, BalatroSetupError


@dataclass(frozen=True)
class SourceMatch:
    line_number: int
    lines: tuple[str, ...]


def start_run_source_matches(
    source: str,
    *,
    context_lines: int = 12,
    max_matches: int = 20,
) -> tuple[SourceMatch, ...]:
    if context_lines < 0:
        raise ValueError("context_lines cannot be negative")
    if max_matches < 1:
        raise ValueError("max_matches must be positive")

    lines = source.splitlines()
    matches: list[SourceMatch] = []
    for index, line in enumerate(lines):
        if "start_run" not in line:
            continue
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)
        numbered = tuple(
            f"{line_index + 1:06d}: {lines[line_index]}"
            for line_index in range(start, end)
        )
        matches.append(SourceMatch(line_number=index + 1, lines=numbered))
        if len(matches) >= max_matches:
            break
    return tuple(matches)


def _main_lua(executable: Path) -> str:
    _infos, _prefix_size, main_lua = _fused_archive(executable)
    return main_lua.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read Balatro's fused main.lua and print source context around every "
            "start_run reference. This is static inspection only: no bridge, "
            "restart, gameplay, or process-memory write is performed."
        )
    )
    parser.add_argument("--balatro-dir")
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--max-matches", type=int, default=20)
    args = parser.parse_args()

    if args.context_lines < 0:
        parser.error("--context-lines cannot be negative")
    if args.max_matches < 1:
        parser.error("--max-matches must be positive")

    try:
        balatro_dir = BalatroSetup.detect_balatro_dir(args.balatro_dir)
        executable = balatro_dir / "Balatro.exe"
        source = _main_lua(executable)
        matches = start_run_source_matches(
            source,
            context_lines=args.context_lines,
            max_matches=args.max_matches,
        )
    except (BalatroSetupError, OSError, RuntimeError, ValueError) as error:
        print("Live restart contract inspection -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print("Live restart contract inspection -> READY")
    print(f"Balatro executable -> {executable}")
    print("Inspection mode -> static fused main.lua only")
    print("Restart command sent -> False")
    print("Gameplay command sent -> False")
    print("Process-memory writes -> False")
    print(f"start_run source matches -> {len(matches)}")

    if not matches:
        print("Result -> no start_run text found in fused main.lua")
        return 3

    for number, match in enumerate(matches, start=1):
        print(f"\n--- start_run match {number} at line {match.line_number} ---")
        for line in match.lines:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
