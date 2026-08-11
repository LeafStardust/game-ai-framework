from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _primitive,
    _table_fields,
)


TARGET_TOKENS = ("play", "discard")
UI_ROOT_HINTS = (
    "button",
    "hud",
    "ui",
    "hand",
    "room",
    "controller",
    "blind",
)
SKIP_NAMES = {
    "GAME",
    "deck",
    "playing_cards",
    "pseudorandom",
    "pseudoseed",
}
MAX_TABLES = 1500
MAX_DEPTH = 5


@dataclass(frozen=True)
class _Candidate:
    path: str
    address: int
    matches: tuple[str, ...]
    geometry: dict[str, float]


def _match_primitive(name: str, value: Any) -> str | None:
    name_text = str(name).casefold()
    value_text = str(value).casefold()
    if any(token in name_text or token in value_text for token in TARGET_TOKENS):
        return f"{name}={value!r}"
    return None


def _walk_ui_tables(decoder, root: dict, *, max_tables: int = MAX_TABLES) -> list[_Candidate]:
    queue: list[tuple[str, int, int]] = []
    for name, value in sorted(root.items()):
        if name in SKIP_NAMES or value.kind != "table":
            continue
        lowered = name.casefold()
        if any(hint in lowered for hint in UI_ROOT_HINTS):
            queue.append((f"G.{name}", int(value.value), 0))

    visited: set[int] = set()
    candidates: list[_Candidate] = []

    while queue and len(visited) < max_tables:
        path, address, depth = queue.pop(0)
        if address in visited:
            continue
        visited.add(address)

        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue

        matches: list[str] = []
        for name, value in fields.items():
            if value.kind in {"string", "integer", "number", "boolean"}:
                primitive = _primitive(value)
                match = _match_primitive(name, primitive)
                if match:
                    matches.append(match)

        if matches:
            candidates.append(
                _Candidate(
                    path=path,
                    address=address,
                    matches=tuple(matches),
                    geometry=_geometry(decoder, fields.get("T")),
                )
            )

        if depth >= MAX_DEPTH:
            continue

        for name, value in sorted(fields.items()):
            if name in SKIP_NAMES or value.kind != "table":
                continue
            lowered = name.casefold()
            # Once inside a UI-ish root, follow normal UI object structure as well
            # as names that look directly relevant to controls.
            if (
                depth == 0
                or any(
                    token in lowered
                    for token in (
                        "child",
                        "node",
                        "button",
                        "config",
                        "definition",
                        "object",
                        "elements",
                        "states",
                        "hand",
                        "play",
                        "discard",
                    )
                )
            ):
                queue.append((f"{path}.{name}", int(value.value), depth + 1))

    return candidates


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            ui_roots = tuple(
                name
                for name, value in sorted(root.items())
                if value.kind == "table"
                and name not in SKIP_NAMES
                and any(hint in name.casefold() for hint in UI_ROOT_HINTS)
            )
            candidates = _walk_ui_tables(decoder, root)
    except Exception as error:
        print("Live hand control geometry probe -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2

    print("Live hand control geometry probe -> DIAGNOSTIC")
    print("Observation source -> live Balatro process memory")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print("UI-ish G roots -> " + (", ".join(ui_roots) if ui_roots else "none"))
    print(f"Play/discard candidate tables -> {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        geometry = candidate.geometry
        geometry_text = (
            " ".join(
                f"{name}={geometry[name]:.6f}"
                for name in ("x", "y", "w", "h", "r", "scale")
                if name in geometry
            )
            if geometry
            else "missing"
        )
        print(
            f"  Candidate {index}: {candidate.path} @ 0x{candidate.address:x}"
        )
        print("    match -> " + "; ".join(candidate.matches))
        print("    T -> " + geometry_text)

    play = [
        candidate
        for candidate in candidates
        if any("play" in match.casefold() for match in candidate.matches)
        and candidate.geometry
    ]
    discard = [
        candidate
        for candidate in candidates
        if any("discard" in match.casefold() for match in candidate.matches)
        and candidate.geometry
    ]

    if len(play) == 1 and len(discard) == 1:
        print("Play Hand live control candidate -> UNIQUE")
        print("Discard live control candidate -> UNIQUE")
        print("Live hand control geometry -> PASS")
        return 0

    print(
        "Play Hand geometry candidates -> "
        + (str(len(play)) if play else "0")
    )
    print(
        "Discard geometry candidates -> "
        + (str(len(discard)) if discard else "0")
    )
    print("Live hand control geometry -> INCONCLUSIVE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
