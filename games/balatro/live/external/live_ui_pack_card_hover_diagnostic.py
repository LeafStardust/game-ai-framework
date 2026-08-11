from __future__ import annotations

import argparse
import time
from collections import deque

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


TOKENS = (
    "select",
    "choose",
    "take",
    "use_card",
    "can_select",
    "can_choose",
    "can_take",
    "can_use",
)
MAX_DEPTH = 6
MAX_TABLES = 500


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _geometry_text(geometry: dict[str, float]) -> str:
    if not geometry:
        return "missing"
    return " ".join(
        f"{name}={geometry[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in geometry
    )


def _pack_cards(decoder, root: dict):
    area = _table_fields(decoder, root.get("pack_cards"))
    cards = _array_table_values(decoder, area.get("cards"))
    return [(position, address) for position, (_, address) in enumerate(cards)]


def _card_description(decoder, address: int):
    card = decoder.string_fields(address)
    base = _table_fields(decoder, card.get("base"))
    ability = _table_fields(decoder, card.get("ability"))
    config = _table_fields(decoder, card.get("config"))
    center = _table_fields(decoder, config.get("center"))
    label = (
        _primitive(card.get("label"))
        or _primitive(ability.get("name"))
        or _primitive(center.get("name"))
    )
    return label, _primitive(base.get("value")), _primitive(base.get("suit")), _geometry(decoder, card.get("T"))


def _matches(name: str, primitive) -> bool:
    text = f"{name} {primitive}".casefold()
    return any(token in text for token in TOKENS)


def _scan_from_value(decoder, start_value, start_path: str):
    start = _table_address(start_value)
    if start is None:
        return [], 0
    queue = deque([(start_path, start, 0)])
    visited: set[int] = set()
    results = []
    while queue and len(visited) < MAX_TABLES:
        path, address, depth = queue.popleft()
        if address in visited:
            continue
        visited.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue
        matches = []
        for name, value in fields.items():
            primitive = _primitive(value)
            if primitive is not None and _matches(name, primitive):
                matches.append(f"{name}={primitive!r}")
        if matches:
            config = _table_fields(decoder, fields.get("config"))
            results.append(
                (
                    path,
                    address,
                    matches,
                    _primitive(config.get("button")),
                    _primitive(config.get("func")),
                    _primitive(config.get("id")),
                    _geometry(decoder, fields.get("T")),
                    _geometry(decoder, fields.get("VT")),
                )
            )
        if depth >= MAX_DEPTH:
            continue
        for name, value in fields.items():
            if value.kind == "table":
                queue.append((f"{path}.{name}", int(value.value), depth + 1))
    return results, len(visited)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hover one live pack card and inspect Balatro's ephemeral selection/take "
            "controls from live memory. Mouse movement only; no click is sent."
        )
    )
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
            if not snapshot.phase.endswith("_PACK"):
                raise RuntimeError(f"Balatro is in {snapshot.phase}, expected *_PACK")
            decoder, _, root = observer._root()
            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
                raise RuntimeError("missing positive G.TILE_W / G.TILE_H")

            cards = _pack_cards(decoder, root)
            matches = [entry for entry in cards if entry[0] == args.index]
            if len(matches) != 1:
                raise RuntimeError(
                    f"expected one pack card at index {args.index}, found {len(matches)}"
                )
            _, card_address = matches[0]
            label, rank, suit, geometry = _card_description(decoder, card_address)
            if not all(name in geometry for name in ("x", "y", "w", "h")):
                raise RuntimeError("target pack card has no complete live geometry")

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)
            transform = BalatroLogicalViewport(float(tile_w), float(tile_h), window.client_rect)
            point = transform.card_center(geometry)
            mouse.move_screen(point)
            if args.settle:
                time.sleep(args.settle)

            decoder, _, root = observer._root()
            controller = _table_fields(decoder, root.get("CONTROLLER"))
            cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
            scans = []
            total_visited = 0
            for name in ("target", "prev_target", "node"):
                results, visited = _scan_from_value(
                    decoder,
                    cursor_hover.get(name),
                    f"G.CONTROLLER.cursor_hover.{name}",
                )
                scans.extend(results)
                total_visited += visited
    except Exception as error:
        print("Live pack card hover diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live pack card hover diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Target index -> {args.index}")
    print(f"Target address -> 0x{card_address:x}")
    print(f"Target label -> {label!r}")
    print(f"Target rank/suit -> {rank!r}/{suit!r}")
    print(f"Target T -> {_geometry_text(geometry)}")
    print(f"Hovered screen center -> x={point.x} y={point.y}")
    print(f"Local UI tables visited -> {total_visited}")
    print(f"Selection/action candidates -> {len(scans)}")
    for index, (path, address, matches, button, func, control_id, t, vt) in enumerate(scans, start=1):
        print(f"  Candidate {index}: {path} @ 0x{address:x}")
        print("    match -> " + "; ".join(matches))
        print(f"    button -> {button!r}")
        print(f"    func -> {func!r}")
        print(f"    id -> {control_id!r}")
        print(f"    T -> {_geometry_text(t)}")
        print(f"    VT -> {_geometry_text(vt)}")

    print(
        "Pack card action discovery -> "
        + ("CANDIDATES_FOUND" if scans else "INCONCLUSIVE")
    )
    return 0 if scans else 1


if __name__ == "__main__":
    raise SystemExit(main())
