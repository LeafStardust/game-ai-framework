from __future__ import annotations

import argparse
import time

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


INTERESTING = (
    "button",
    "func",
    "id",
    "click",
    "select",
    "choose",
    "use",
    "take",
    "hover",
    "drag",
    "release",
)


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _pack_cards(decoder, root: dict) -> list[int]:
    area = _table_fields(decoder, root.get("pack_cards"))
    return [address for _, address in _array_table_values(decoder, area.get("cards"))]


def _describe_table(decoder, label: str, address: int) -> None:
    fields = decoder.string_fields(address)
    print(f"{label} @ 0x{address:x}")
    primitives = []
    for name, value in sorted(fields.items()):
        primitive = _primitive(value)
        if primitive is None:
            continue
        text = f"{name} {primitive}".casefold()
        if any(token in text for token in INTERESTING):
            primitives.append(f"{name}={primitive!r}")
    print("  interesting primitives -> " + ("; ".join(primitives) if primitives else "none"))
    print(f"  T -> {_geometry(decoder, fields.get('T'))}")
    print(f"  VT -> {_geometry(decoder, fields.get('VT'))}")
    config = _table_fields(decoder, fields.get("config"))
    if config:
        values = []
        for name, value in sorted(config.items()):
            primitive = _primitive(value)
            if primitive is not None:
                values.append(f"{name}={primitive!r}")
        print("  config -> " + ("; ".join(values) if values else "no primitive fields"))
    states = _table_fields(decoder, fields.get("states"))
    if states:
        state_names = []
        for name, value in sorted(states.items()):
            if value.kind == "table":
                nested = _table_fields(decoder, value)
                nested_values = []
                for nested_name, nested_value in sorted(nested.items()):
                    primitive = _primitive(nested_value)
                    if primitive is not None:
                        nested_values.append(f"{nested_name}={primitive!r}")
                state_names.append(f"{name}({', '.join(nested_values)})")
            else:
                primitive = _primitive(value)
                if primitive is not None:
                    state_names.append(f"{name}={primitive!r}")
        print("  states -> " + ("; ".join(state_names) if state_names else "no primitive fields"))
    children = _table_fields(decoder, fields.get("children"))
    if children:
        print("  children -> " + ", ".join(sorted(children)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hover one pack card and inspect the card plus its live parent chain for "
            "action identity/callback metadata. Mouse movement only; no click is sent."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--settle", type=float, default=0.30)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")

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
            cards = _pack_cards(decoder, root)
            if args.index >= len(cards):
                raise RuntimeError(f"index {args.index} out of range for {len(cards)} pack cards")
            card_address = cards[args.index]
            card = decoder.string_fields(card_address)
            geometry = _geometry(decoder, card.get("T"))
            if tile_w is None or tile_h is None or not all(k in geometry for k in ("x", "y", "w", "h")):
                raise RuntimeError("missing live viewport/card geometry")

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
            target_address = _table_address(cursor_hover.get("target"))

            print("Live pack card action identity diagnostic -> PASS")
            print("Observation source -> live Balatro process memory")
            print(f"Phase -> {snapshot.phase}")
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> False")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Pack card index -> {args.index}")
            print(f"Pack card address -> 0x{card_address:x}")
            print(f"Hovered screen center -> x={point.x} y={point.y}")
            print(f"cursor_hover.target -> {('0x%x' % target_address) if target_address is not None else 'missing'}")

            address = card_address
            seen = set()
            for depth in range(8):
                if address is None or address in seen:
                    break
                seen.add(address)
                _describe_table(decoder, f"Chain[{depth}]", address)
                fields = decoder.string_fields(address)
                address = _table_address(fields.get("parent"))
            return 0
    except Exception as error:
        print("Live pack card action identity diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
