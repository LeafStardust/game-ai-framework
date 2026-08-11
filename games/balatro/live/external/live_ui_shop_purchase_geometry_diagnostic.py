from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


AREA_PAYLOADS = {
    "main": "shop_jokers",
    "boosters": "shop_boosters",
    "vouchers": "shop_vouchers",
}
REQUIRED_GEOMETRY = ("x", "y", "w", "h")


@dataclass(frozen=True)
class PurchaseControl:
    name: str
    container_address: int
    ui_root_address: int
    button: object
    func: object
    control_id: object
    container_t: dict[str, float]
    container_vt: dict[str, float]
    ui_root_t: dict[str, float]
    ui_root_vt: dict[str, float]


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


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


def _screen_text(transform, geometry: dict[str, float]) -> str:
    if not _complete(geometry):
        return "unavailable"
    rect = transform.screen_rect(
        x=float(geometry["x"]),
        y=float(geometry["y"]),
        w=float(geometry["w"]),
        h=float(geometry["h"]),
    )
    center = transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )
    return (
        f"rect=left={rect.left} top={rect.top} width={rect.width} height={rect.height}; "
        f"center=x={center.x} y={center.y}"
    )


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


def _resolve_controls(decoder, root: dict) -> list[PurchaseControl]:
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    prev_target = _table_fields(decoder, cursor_hover.get("prev_target"))
    children = _table_fields(decoder, prev_target.get("children"))
    if not children:
        raise RuntimeError(
            "G.CONTROLLER.cursor_hover.prev_target.children is unavailable"
        )

    result: list[PurchaseControl] = []
    for name in ("buy_button", "buy_and_use_button"):
        container_value = children.get(name)
        container_address = _table_address(container_value)
        if container_address is None:
            continue
        container = _table_fields(decoder, container_value)
        ui_root_value = container.get("UIRoot")
        ui_root_address = _table_address(ui_root_value)
        if ui_root_address is None:
            continue
        ui_root = _table_fields(decoder, ui_root_value)
        config = _table_fields(decoder, ui_root.get("config"))
        result.append(
            PurchaseControl(
                name=name,
                container_address=container_address,
                ui_root_address=ui_root_address,
                button=_primitive(config.get("button")),
                func=_primitive(config.get("func")),
                control_id=_primitive(config.get("id")),
                container_t=_geometry(decoder, container.get("T")),
                container_vt=_geometry(decoder, container.get("VT")),
                ui_root_t=_geometry(decoder, ui_root.get("T")),
                ui_root_vt=_geometry(decoder, ui_root.get("VT")),
            )
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hover one live-memory-derived Balatro SHOP item and resolve the owning "
            "Buy / Buy & Use UI nodes and screen geometry. No mouse click is sent."
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
            card_geometry = card.get("ui") or {}
            if not _complete(card_geometry):
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
            hover_point = transform.card_center(card_geometry)
            mouse.move_screen(hover_point)
            if args.settle:
                time.sleep(args.settle)

            decoder, _, root = observer._root()
            controls = _resolve_controls(decoder, root)
    except Exception as error:
        print("Live SHOP purchase geometry diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    label = card.get("label") or card.get("ability_name") or card.get("center")
    print("Live SHOP purchase geometry diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Target area -> {args.area}")
    print(f"Target index -> {args.index}")
    print(f"Target label -> {label!r}")
    print(f"Hovered screen center -> x={hover_point.x} y={hover_point.y}")
    print(
        "Balatro client rect -> "
        f"left={window.client_rect.left} top={window.client_rect.top} "
        f"width={window.client_rect.width} height={window.client_rect.height}"
    )
    print(f"G.TILE_W -> {float(tile_w)}")
    print(f"G.TILE_H -> {float(tile_h)}")
    print(f"Purchase controls resolved -> {len(controls)}")

    for index, control in enumerate(controls, start=1):
        print(f"  Control {index}: {control.name}")
        print(f"    Container address -> 0x{control.container_address:x}")
        print(f"    UIRoot address -> 0x{control.ui_root_address:x}")
        print(f"    button -> {control.button!r}")
        print(f"    func -> {control.func!r}")
        print(f"    id -> {control.control_id!r}")
        print("    Container T -> " + _geometry_text(control.container_t))
        print("    Container VT -> " + _geometry_text(control.container_vt))
        print("    UIRoot T -> " + _geometry_text(control.ui_root_t))
        print("    UIRoot VT -> " + _geometry_text(control.ui_root_vt))

        if _complete(control.ui_root_vt):
            selected_name = "UIRoot VT"
            selected = control.ui_root_vt
        elif _complete(control.ui_root_t):
            selected_name = "UIRoot T"
            selected = control.ui_root_t
        elif _complete(control.container_vt):
            selected_name = "Container VT"
            selected = control.container_vt
        else:
            selected_name = "Container T"
            selected = control.container_t
        print(f"    Geometry source selected -> {selected_name}")
        print("    Screen geometry -> " + _screen_text(transform, selected))

    if not controls:
        print("SHOP purchase control geometry -> INCONCLUSIVE")
        return 1

    actionable = [
        control
        for control in controls
        if control.button == "buy_from_shop"
        and (
            _complete(control.ui_root_vt)
            or _complete(control.ui_root_t)
            or _complete(control.container_vt)
            or _complete(control.container_t)
        )
    ]
    print(
        "SHOP purchase control geometry -> "
        + ("READY" if actionable else "INCONCLUSIVE")
    )
    return 0 if actionable else 1


if __name__ == "__main__":
    raise SystemExit(main())
