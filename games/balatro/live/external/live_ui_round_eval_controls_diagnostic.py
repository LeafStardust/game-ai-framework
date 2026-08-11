from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _primitive,
)


TOKENS = (
    "cash",
    "collect",
    "reward",
    "payout",
    "shop",
    "continue",
    "round_eval",
    "round eval",
)
ROOT_HINTS = (
    "ui",
    "round",
    "eval",
    "cash",
    "reward",
    "button",
    "hud",
    "room",
    "controller",
)
SKIP_ROOTS = {
    "GAME",
    "deck",
    "playing_cards",
    "pseudorandom",
    "pseudoseed",
}
MAX_DEPTH = 8
MAX_TABLES = 5000


@dataclass(frozen=True)
class Candidate:
    path: str
    address: int
    matches: tuple[str, ...]
    geometry: dict[str, float]


def _safe_fields(decoder, address: int) -> dict:
    try:
        return decoder.string_fields(int(address))
    except Exception:
        return {}


def _array_children(decoder, address: int) -> list[tuple[int, int]]:
    try:
        items = decoder.array_items(int(address))
    except Exception:
        return []
    return [
        (index, int(value.value))
        for index, value in items
        if value.kind == "table"
    ]


def _match(name: str, value: Any) -> bool:
    name_text = str(name).strip().casefold()
    value_text = str(value).strip().casefold()
    return any(token in name_text or token in value_text for token in TOKENS)


def _root_candidates(root: dict) -> list[tuple[str, int]]:
    preferred: list[tuple[str, int]] = []
    fallback: list[tuple[str, int]] = []
    for name, value in sorted(root.items()):
        if name in SKIP_ROOTS or value.kind != "table":
            continue
        item = (name, int(value.value))
        fallback.append(item)
        if any(hint in name.casefold() for hint in ROOT_HINTS):
            preferred.append(item)
    return preferred or fallback


def _scan(decoder, root: dict) -> tuple[list[Candidate], int, tuple[str, ...]]:
    roots = _root_candidates(root)
    queue = deque((f"G.{name}", address, 0) for name, address in roots)
    visited: set[int] = set()
    candidates: list[Candidate] = []

    while queue and len(visited) < MAX_TABLES:
        path, address, depth = queue.popleft()
        if address in visited:
            continue
        visited.add(address)

        fields = _safe_fields(decoder, address)
        if not fields:
            continue

        matches: list[str] = []
        for name, value in sorted(fields.items()):
            primitive = _primitive(value)
            if primitive is None:
                continue
            if _match(name, primitive):
                matches.append(f"{name}={primitive!r}")

        geometry = _geometry(decoder, fields.get("T"))
        if matches:
            candidates.append(
                Candidate(
                    path=path,
                    address=address,
                    matches=tuple(matches),
                    geometry=geometry,
                )
            )

        if depth >= MAX_DEPTH:
            continue

        for name, value in sorted(fields.items()):
            if value.kind == "table":
                queue.append((f"{path}.{name}", int(value.value), depth + 1))
        for index, child in _array_children(decoder, address):
            queue.append((f"{path}[{index + 1}]", child, depth + 1))

    return candidates, len(visited), tuple(name for name, _ in roots)


def _geometry_text(geometry: dict[str, float]) -> str:
    if not geometry:
        return "missing"
    return " ".join(
        f"{name}={geometry[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in geometry
    )


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            snapshot = observer.observe()
            candidates, visited, roots = _scan(decoder, root)
    except Exception as error:
        print("Live ROUND_EVAL control diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2

    print("Live ROUND_EVAL control diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print("Traversal roots -> " + (", ".join(roots) if roots else "none"))
    print(f"UI tables visited -> {visited}")
    print(f"Cash/reward/control candidates -> {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        print(f"  Candidate {index}: {candidate.path} @ 0x{candidate.address:x}")
        print("    match -> " + "; ".join(candidate.matches))
        print("    T -> " + _geometry_text(candidate.geometry))

    if snapshot.phase != "ROUND_EVAL":
        print("ROUND_EVAL phase guard -> FAIL")
        return 1
    if not candidates:
        print("ROUND_EVAL cash-out control discovery -> INCONCLUSIVE")
        return 1

    print("ROUND_EVAL cash-out control discovery -> CANDIDATES_FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
