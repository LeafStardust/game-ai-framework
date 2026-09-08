from __future__ import annotations

import argparse
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from games.balatro.live.injected.install import BRIDGE_ARCHIVE_NAME
from games.balatro.setup.installer import BalatroSetup, BalatroSetupError


@dataclass(frozen=True)
class SourceMatch:
    line_number: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveSourceMatch:
    source_name: str
    line_number: int
    lines: tuple[str, ...]


def source_matches(
    source: str,
    pattern: str,
    *,
    context_lines: int = 12,
    max_matches: int = 20,
) -> tuple[SourceMatch, ...]:
    if not pattern:
        raise ValueError("pattern cannot be empty")
    if context_lines < 0:
        raise ValueError("context_lines cannot be negative")
    if max_matches < 1:
        raise ValueError("max_matches must be positive")

    lines = source.splitlines()
    matches: list[SourceMatch] = []
    for index, line in enumerate(lines):
        if pattern not in line:
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


def archive_matches(
    sources: Mapping[str, str],
    pattern: str,
    *,
    context_lines: int = 12,
    max_matches: int = 20,
) -> tuple[ArchiveSourceMatch, ...]:
    if not pattern:
        raise ValueError("pattern cannot be empty")
    if context_lines < 0:
        raise ValueError("context_lines cannot be negative")
    if max_matches < 1:
        raise ValueError("max_matches must be positive")

    matches: list[ArchiveSourceMatch] = []
    for source_name in sorted(sources):
        remaining = max_matches - len(matches)
        if remaining <= 0:
            break
        for match in source_matches(
            sources[source_name],
            pattern,
            context_lines=context_lines,
            max_matches=remaining,
        ):
            matches.append(
                ArchiveSourceMatch(
                    source_name=source_name,
                    line_number=match.line_number,
                    lines=match.lines,
                )
            )
    return tuple(matches)


def start_run_source_matches(
    source: str,
    *,
    context_lines: int = 12,
    max_matches: int = 20,
) -> tuple[SourceMatch, ...]:
    return source_matches(
        source,
        "start_run",
        context_lines=context_lines,
        max_matches=max_matches,
    )


def start_run_archive_matches(
    sources: Mapping[str, str],
    *,
    context_lines: int = 12,
    max_matches: int = 20,
) -> tuple[ArchiveSourceMatch, ...]:
    return archive_matches(
        sources,
        "start_run",
        context_lines=context_lines,
        max_matches=max_matches,
    )


def _lua_sources(executable: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    with zipfile.ZipFile(executable, "r") as archive:
        for info in archive.infolist():
            name = info.filename
            if not name.lower().endswith(".lua"):
                continue
            # Ignore our injected bridge so its own diagnostics cannot masquerade
            # as evidence about Balatro's native call contract.
            if name == BRIDGE_ARCHIVE_NAME:
                continue
            sources[name] = archive.read(info).decode("utf-8", errors="replace")
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read every native Lua source in Balatro's fused archive and print "
            "context around an exact source pattern. This is static inspection "
            "only: no bridge, restart, gameplay, or process-memory write is performed."
        )
    )
    parser.add_argument("--balatro-dir")
    parser.add_argument("--pattern", default="start_run")
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--max-matches", type=int, default=20)
    args = parser.parse_args()

    if not args.pattern:
        parser.error("--pattern cannot be empty")
    if args.context_lines < 0:
        parser.error("--context-lines cannot be negative")
    if args.max_matches < 1:
        parser.error("--max-matches must be positive")

    try:
        balatro_dir = BalatroSetup.detect_balatro_dir(args.balatro_dir)
        executable = balatro_dir / "Balatro.exe"
        sources = _lua_sources(executable)
        matches = archive_matches(
            sources,
            args.pattern,
            context_lines=args.context_lines,
            max_matches=args.max_matches,
        )
    except (BalatroSetupError, OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print("Live restart contract inspection -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print("Live restart contract inspection -> READY")
    print(f"Balatro executable -> {executable}")
    print("Inspection mode -> static fused native Lua archive only")
    print("Injected bridge source excluded -> True")
    print("Restart command sent -> False")
    print("Gameplay command sent -> False")
    print("Process-memory writes -> False")
    print(f"Lua sources scanned -> {len(sources)}")
    print(f"Source pattern -> {args.pattern}")
    print(f"Source matches -> {len(matches)}")

    if not matches:
        print(f"Result -> no {args.pattern!r} text found in native fused Lua sources")
        return 3

    for number, match in enumerate(matches, start=1):
        print(
            f"\n--- pattern match {number}: {match.source_name} "
            f"line {match.line_number} ---"
        )
        for line in match.lines:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
