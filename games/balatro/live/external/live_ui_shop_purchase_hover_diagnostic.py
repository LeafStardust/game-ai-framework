from __future__ import annotations

import argparse
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _primitive,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


AREA_PAYLOADS = {
    "main": "shop_jokers",
    "boosters": "shop_boosters",
    "vouchers": "shop_vouchers",
}
TOKENS = (
    "buy",
    "purchase",
    "buy_and_use",
    "buy and use",
    "use_card",
)
ROOT_HINTS = (
    "controller",
    "ui",
    "shop",
    "button",
    "room",
)
SKIP_ROOTS = {
    "GAME",
    "deck",
    "playing_cards",
    "pseudorandom",
    "pseudoseed",
}
MAX_DEPTH = 10
MAX_TABLES = 8000
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


def _complete(geometry: dict[str, float]) -> bool:
    return all(name in geometry for name in REQUIRED_GEOMETRY)


def _geometry_text(geometry: dict[str, float]) -> str:
    if not geometry:
        return "missing"
    return " ".join(
        f"{name}={geometry[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in geometry
    )


def _screen_center(transform, geometry: dict[str, float]) -> str:
    if not _complete(geometry):
        return "unavailable"
    point = transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )
    return f"x={point.x} y={point.y}"


def _target_card(snapshot, area: str, index: int) -> dict:
    payload_name = AREA_PAYLOADS[area]
    cards = (snapshot.payload.get(payload_name) or {}).get("cards") or []
    matches = [
        card
        for position, card in enumerate(cards)
        if int(card.get("area_index", position)) == index
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one visible {area} shop item at index {index}, "
            f"found {len(matches)}"
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hover one live-memory-derived Balatro SHOP item with the normal Windows "
            "cursor, then scan live UI memory for Buy/Buy & Use controls. No click is sent."
        )
    )
    parser.add_argument("--area", choices=sorted(AREA_PAYLOADS), default="main")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--settle", type=float, default=0.40)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")
    if args.settle < 0:
        parser.error("--settle cannot be negative")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
            if snapshot.phase != "SHOP":
                raise RuntimeError(f"Balatro is in {snapshot.phase}, expected SHOP")

            decoder, _, root = observer._root()
            card = _target_card(snapshot, args.area, args.index)
            geometry = card.get("ui") or {}
            if not _complete(geometry):
                raise RuntimeError("target shop item has no complete live T geometry")

            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
                raise RuntimeError("missing positive G.TILE_W / G.TILE_H")

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            point = transform.card_center(geometry)
            mouse.move_screen(point)
            if args.settle:
                time.sleep(args.settle)

            # Re-read the live root after hover because Balatro may create or attach
            # the purchase UI only after the cursor enters the card.
            decoder, _, root = observer._root()
            candidates, visited, roots = _scan(decoder, root)
    except Exception as error:
        print("Live SHOP purchase hover diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse movement sent -> False or incomplete")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    label = card.get("label") or card.get("ability_name") or card.get("center")
    cost = card.get("cost")
    print("Live SHOP purchase hover diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Target area -> {args.area}")
    print(f"Target index -> {args.index}")
    print(f"Target label -> {label!r}")
    print(f"Target cost -> {cost!r}")
    print(f"Target T -> {_geometry_text(geometry)}")
    print(f"Hovered screen center -> x={point.x} y={point.y}")
    print("Traversal roots -> " + (", ".join(roots) if roots else "none"))
    print(f"UI tables visited -> {visited}")
    print(f"Buy/purchase candidates -> {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        print(f"  Candidate {index}: {candidate.path} @ 0x{candidate.address:x}")
        print("    match -> " + "; ".join(candidate.matches))
        print("    T -> " + _geometry_text(candidate.t))
        print("    VT -> " + _geometry_text(candidate.vt))
        selected = candidate.vt if _complete(candidate.vt) else candidate.t
        print("    Screen center -> " + _screen_center(transform, selected))

    if not candidates:
        print("SHOP purchase control discovery -> INCONCLUSIVE")
        return 1

    print("SHOP purchase control discovery -> CANDIDATES_FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
