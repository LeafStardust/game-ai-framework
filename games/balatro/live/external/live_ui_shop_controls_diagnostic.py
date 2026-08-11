from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _primitive,
)
from .live_ui_transform import BalatroLogicalViewport
from .window import BalatroWindowLocator


TOKENS = (
    "next_round",
    "next round",
    "reroll",
    "reroll_shop",
    "buy",
    "purchase",
    "shop",
    "voucher",
    "booster",
)
ROOT_HINTS = (
    "ui",
    "shop",
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
MAX_DEPTH = 9
MAX_TABLES = 7000
REQUIRED_GEOMETRY = ("x", "y", "w", "h")


@dataclass(frozen=True)
class Candidate:
    path: str
    address: int
    matches: tuple[str, ...]
    t: dict[str, float]
    vt: dict[str, float]


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

        if matches:
            candidates.append(
                Candidate(
                    path=path,
                    address=address,
                    matches=tuple(matches),
                    t=_geometry(decoder, fields.get("T")),
                    vt=_geometry(decoder, fields.get("VT")),
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


def _complete(geometry: dict[str, float]) -> bool:
    return all(name in geometry for name in REQUIRED_GEOMETRY)


def _screen_center(transform, geometry: dict[str, float]) -> str:
    if not _complete(geometry):
        return "unavailable"
    point = transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )
    return f"x={point.x} y={point.y}"


def _shop_items(payload: dict) -> list[tuple[str, int, dict]]:
    result: list[tuple[str, int, dict]] = []
    for area in ("shop_jokers", "shop_boosters", "shop_vouchers"):
        cards = (payload.get(area) or {}).get("cards") or []
        for position, card in enumerate(cards):
            index = card.get("area_index", position)
            result.append((area, int(index), card))
    return result


def main() -> int:
    try:
        window = BalatroWindowLocator().find()
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            snapshot = observer.observe()
            candidates, visited, roots = _scan(decoder, root)

            tile_w = _primitive(root.get("TILE_W"))
            tile_h = _primitive(root.get("TILE_H"))
            if not isinstance(tile_w, (int, float)) or not isinstance(tile_h, (int, float)):
                raise RuntimeError("missing numeric G.TILE_W / G.TILE_H")
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
    except Exception as error:
        print("Live SHOP control diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live SHOP control diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(
        "Balatro client rect -> "
        f"left={window.client_rect.left} top={window.client_rect.top} "
        f"width={window.client_rect.width} height={window.client_rect.height}"
    )

    items = _shop_items(snapshot.payload)
    print(f"Visible shop items -> {len(items)}")
    for area, index, card in items:
        geometry = card.get("ui") or {}
        label = card.get("label") or card.get("ability_name") or card.get("center")
        cost = card.get("cost")
        print(f"  {area}[{index}] -> label={label!r}; cost={cost!r}")
        print(f"    T -> {_geometry_text(geometry)}")
        print(f"    Screen center -> {_screen_center(transform, geometry)}")

    print("Traversal roots -> " + (", ".join(roots) if roots else "none"))
    print(f"UI tables visited -> {visited}")
    print(f"Shop/control candidates -> {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        print(f"  Candidate {index}: {candidate.path} @ 0x{candidate.address:x}")
        print("    match -> " + "; ".join(candidate.matches))
        print("    T -> " + _geometry_text(candidate.t))
        print("    VT -> " + _geometry_text(candidate.vt))
        geometry = candidate.vt if _complete(candidate.vt) else candidate.t
        print("    Screen center -> " + _screen_center(transform, geometry))

    if snapshot.phase != "SHOP":
        print("SHOP phase guard -> FAIL")
        return 1
    if not items:
        print("SHOP item geometry discovery -> INCONCLUSIVE")
        return 1
    if not candidates:
        print("SHOP auxiliary control discovery -> INCONCLUSIVE")
        return 1

    print("SHOP item geometry discovery -> CANDIDATES_FOUND")
    print("SHOP auxiliary control discovery -> CANDIDATES_FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
