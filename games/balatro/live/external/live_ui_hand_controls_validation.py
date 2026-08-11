from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _primitive,
)


PLAY_VALUES = {
    "play hand",
    "play_hand",
    "play cards",
    "play_cards",
    "play_cards_from_highlighted",
}
DISCARD_VALUES = {
    "discard",
    "discard hand",
    "discard_hand",
    "discard cards",
    "discard_cards",
    "discard_cards_from_highlighted",
}
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
MAX_TABLES = 5000
MAX_DEPTH = 8


@dataclass(frozen=True)
class _Candidate:
    kind: str
    path: str
    address: int
    matches: tuple[str, ...]
    geometry: dict[str, float]
    geometry_path: str | None


def _normalized(value: Any) -> str:
    text = str(value).strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return text


def _classify_primitive(name: str, value: Any) -> str | None:
    """Classify only explicit button labels/callbacks, never substring matches.

    In particular, ``playing_card`` must not be mistaken for a Play Hand control.
    """

    name_text = _normalized(name)
    value_text = _normalized(value)

    if value_text in PLAY_VALUES or name_text in PLAY_VALUES:
        return "play"
    if value_text in DISCARD_VALUES or name_text in DISCARD_VALUES:
        return "discard"
    return None


def _safe_string_fields(decoder, address: int) -> dict:
    try:
        return decoder.string_fields(address)
    except Exception:
        return {}


def _array_table_children(decoder, address: int) -> list[tuple[int, int]]:
    try:
        items = decoder.array_items(address)
    except Exception:
        return []
    return [
        (index, int(value.value))
        for index, value in items
        if value.kind == "table"
    ]


def _walk_ui_tables(
    decoder,
    root: dict,
    *,
    max_tables: int = MAX_TABLES,
) -> tuple[list[_Candidate], int]:
    # path, address, depth, nearest geometry, nearest geometry path
    queue: list[tuple[str, int, int, dict[str, float], str | None]] = []
    for name, value in sorted(root.items()):
        if name in SKIP_NAMES or value.kind != "table":
            continue
        lowered = name.casefold()
        if any(hint in lowered for hint in UI_ROOT_HINTS):
            queue.append((f"G.{name}", int(value.value), 0, {}, None))

    visited: set[int] = set()
    candidates: list[_Candidate] = []

    while queue and len(visited) < max_tables:
        path, address, depth, inherited_geometry, inherited_geometry_path = queue.pop(0)
        if address in visited:
            continue
        visited.add(address)

        fields = _safe_string_fields(decoder, address)
        if not fields:
            continue

        own_geometry = _geometry(decoder, fields.get("T"))
        if own_geometry:
            nearest_geometry = own_geometry
            nearest_geometry_path = path
        else:
            nearest_geometry = inherited_geometry
            nearest_geometry_path = inherited_geometry_path

        matches: dict[str, list[str]] = {"play": [], "discard": []}
        for name, value in fields.items():
            if value.kind not in {"string", "integer", "number", "boolean"}:
                continue
            primitive = _primitive(value)
            kind = _classify_primitive(name, primitive)
            if kind is not None:
                matches[kind].append(f"{name}={primitive!r}")

        for kind in ("play", "discard"):
            if matches[kind]:
                candidates.append(
                    _Candidate(
                        kind=kind,
                        path=path,
                        address=address,
                        matches=tuple(matches[kind]),
                        geometry=dict(nearest_geometry),
                        geometry_path=nearest_geometry_path,
                    )
                )

        if depth >= MAX_DEPTH:
            continue

        # Follow every table-valued field once we are inside an explicitly UI-ish
        # root. Balatro UIBox/UIElement trees often hide controls under generic
        # ``children``/``nodes``/``config`` tables whose names alone are not enough.
        for name, value in sorted(fields.items()):
            if name in SKIP_NAMES or value.kind != "table":
                continue
            queue.append(
                (
                    f"{path}.{name}",
                    int(value.value),
                    depth + 1,
                    nearest_geometry,
                    nearest_geometry_path,
                )
            )

        # Lua UI node collections are commonly array-backed rather than exposed
        # through string fields. The first probe missed these entirely.
        for index, child_address in _array_table_children(decoder, address):
            queue.append(
                (
                    f"{path}[{index + 1}]",
                    child_address,
                    depth + 1,
                    nearest_geometry,
                    nearest_geometry_path,
                )
            )

    return candidates, len(visited)


def _candidate_geometry_text(candidate: _Candidate) -> str:
    geometry = candidate.geometry
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
            ui_roots = tuple(
                name
                for name, value in sorted(root.items())
                if value.kind == "table"
                and name not in SKIP_NAMES
                and any(hint in name.casefold() for hint in UI_ROOT_HINTS)
            )
            candidates, visited_count = _walk_ui_tables(decoder, root)
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
    print(f"UI tables visited -> {visited_count}")
    print(f"Explicit play/discard candidate tables -> {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"  Candidate {index}: {candidate.kind.upper()} "
            f"{candidate.path} @ 0x{candidate.address:x}"
        )
        print("    match -> " + "; ".join(candidate.matches))
        print("    T -> " + _candidate_geometry_text(candidate))
        print(
            "    geometry source -> "
            + (candidate.geometry_path or "none")
        )

    play = [candidate for candidate in candidates if candidate.kind == "play" and candidate.geometry]
    discard = [
        candidate
        for candidate in candidates
        if candidate.kind == "discard" and candidate.geometry
    ]

    print(f"Play Hand geometry candidates -> {len(play)}")
    print(f"Discard geometry candidates -> {len(discard)}")

    if len(play) == 1 and len(discard) == 1:
        print("Play Hand live control candidate -> UNIQUE")
        print("Discard live control candidate -> UNIQUE")
        print("Live hand control geometry -> PASS")
        return 0

    print("Live hand control geometry -> INCONCLUSIVE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
