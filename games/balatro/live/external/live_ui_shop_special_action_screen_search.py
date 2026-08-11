from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from .live_memory_observer import LiveMemoryBalatroObserver, _number, _primitive, _table_fields
from .live_shop_purchase_mouse import resolve_live_shop_item_target
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator


AREA_PAYLOADS = {
    "vouchers": "shop_vouchers",
    "boosters": "shop_boosters",
}
EXPECTED = {
    "vouchers": (None, "can_redeem"),
    "boosters": ("use_card", "can_open"),
}
MAX_PARENT_DEPTH = 12


@dataclass(frozen=True)
class ActionHit:
    point: PixelPoint
    signal: str
    address: int
    button: object
    func: object
    control_id: object


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _target_card(snapshot, area: str, index: int) -> dict:
    cards = (snapshot.payload.get(AREA_PAYLOADS[area]) or {}).get("cards") or []
    matches = [
        card
        for position, card in enumerate(cards)
        if int(card.get("area_index", position)) == index
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one visible {area} item at index {index}, found {len(matches)}"
        )
    return matches[0]


def _resolve_expected_from_node(decoder, value, signal: str, area: str):
    expected_button, expected_func = EXPECTED[area]
    address = _table_address(value)
    seen: set[int] = set()
    depth = 0
    while address is not None and address not in seen and depth < MAX_PARENT_DEPTH:
        seen.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            return None
        config = _table_fields(decoder, fields.get("config"))
        button = _primitive(config.get("button"))
        func = _primitive(config.get("func"))
        control_id = _primitive(config.get("id"))
        if func == expected_func and (expected_button is None or button == expected_button):
            return address, button, func, control_id, f"{signal}.parent[{depth}]"
        address = _table_address(fields.get("parent"))
        depth += 1
    return None


def _current_hit(observer, point: PixelPoint, area: str) -> ActionHit | None:
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        resolved = _resolve_expected_from_node(
            decoder,
            cursor_hover.get(name),
            f"cursor_hover.{name}",
            area,
        )
        if resolved is not None:
            address, button, func, control_id, signal = resolved
            return ActionHit(point, signal, address, button, func, control_id)
    return None


def _probe(observer, mouse, item_point, point, area, *, card_settle, probe_settle):
    # Re-hover the item before every probe because its action UI is ephemeral.
    mouse.move_screen(item_point)
    if card_settle:
        time.sleep(card_settle)
    mouse.move_screen(point)
    if probe_settle:
        time.sleep(probe_settle)
    return _current_hit(observer, point, area)


def _search_points(item_point: PixelPoint, rect, step: int) -> list[PixelPoint]:
    left = max(rect.left, item_point.x - 220)
    right = min(rect.right - 1, item_point.x + 220)
    top = max(rect.top, item_point.y - 220)
    bottom = min(rect.bottom - 1, item_point.y + 180)
    points = [
        PixelPoint(x, y)
        for y in range(top, bottom + 1, step)
        for x in range(left, right + 1, step)
    ]
    points.sort(key=lambda p: abs(p.x - item_point.x) + abs(p.y - item_point.y))
    return points


def _scan_edge(observer, mouse, item_point, origin, area, *, axis, direction, step, max_distance, card_settle, probe_settle):
    last = origin.x if axis == "x" else origin.y
    for distance in range(step, max_distance + step, step):
        if axis == "x":
            point = PixelPoint(origin.x + direction * distance, origin.y)
        else:
            point = PixelPoint(origin.x, origin.y + direction * distance)
        hit = _probe(
            observer,
            mouse,
            item_point,
            point,
            area,
            card_settle=card_settle,
            probe_settle=probe_settle,
        )
        if hit is None:
            break
        last = point.x if axis == "x" else point.y
    return last


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Locate the live Voucher Redeem or Booster Open control using normal mouse "
            "movement and Balatro cursor-hover identity. No click is sent."
        )
    )
    parser.add_argument("--area", choices=sorted(AREA_PAYLOADS), required=True)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--coarse-step", type=int, default=20)
    parser.add_argument("--fine-step", type=int, default=4)
    parser.add_argument("--card-settle", type=float, default=0.10)
    parser.add_argument("--probe-settle", type=float, default=0.08)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")
    if args.coarse_step <= 0 or args.fine_step <= 0:
        parser.error("scan steps must be positive")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
            if snapshot.phase != "SHOP":
                raise RuntimeError(f"Balatro is in {snapshot.phase}, expected SHOP")

            decoder, _, root = observer._root()
            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
                raise RuntimeError("missing positive G.TILE_W / G.TILE_H")

            card = _target_card(snapshot, args.area, args.index)
            geometry = card.get("ui") or {}
            transform = BalatroLogicalViewport(float(tile_w), float(tile_h), window.client_rect)
            item_point = transform.card_center(geometry)

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)
            transform = BalatroLogicalViewport(float(tile_w), float(tile_h), window.client_rect)
            item_point = transform.card_center(geometry)

            first_hit = None
            probes = 0
            for point in _search_points(item_point, window.client_rect, args.coarse_step):
                probes += 1
                first_hit = _probe(
                    observer,
                    mouse,
                    item_point,
                    point,
                    args.area,
                    card_settle=args.card_settle,
                    probe_settle=args.probe_settle,
                )
                if first_hit is not None:
                    break

            if first_hit is None:
                print("Live SHOP special action screen search -> INCONCLUSIVE")
                print("Observation source -> live Balatro process memory")
                print(f"Area -> {args.area}")
                print("Mouse movement sent -> True")
                print("Mouse clicks sent -> False")
                print(f"Item hover center -> x={item_point.x} y={item_point.y}")
                print(f"Coarse probes attempted -> {probes}")
                return 1

            origin = first_hit.point
            left = _scan_edge(observer, mouse, item_point, origin, args.area, axis="x", direction=-1, step=args.fine_step, max_distance=180, card_settle=args.card_settle, probe_settle=args.probe_settle)
            right = _scan_edge(observer, mouse, item_point, origin, args.area, axis="x", direction=1, step=args.fine_step, max_distance=180, card_settle=args.card_settle, probe_settle=args.probe_settle)
            top = _scan_edge(observer, mouse, item_point, origin, args.area, axis="y", direction=-1, step=args.fine_step, max_distance=140, card_settle=args.card_settle, probe_settle=args.probe_settle)
            bottom = _scan_edge(observer, mouse, item_point, origin, args.area, axis="y", direction=1, step=args.fine_step, max_distance=140, card_settle=args.card_settle, probe_settle=args.probe_settle)
            center = PixelPoint(round((left + right) / 2), round((top + bottom) / 2))
            center_hit = _probe(
                observer,
                mouse,
                item_point,
                center,
                args.area,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
            )
    except Exception as error:
        print("Live SHOP special action screen search -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    label = card.get("label") or card.get("ability_name") or card.get("center")
    print("Live SHOP special action screen search -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print(f"Area -> {args.area}")
    print(f"Target index -> {args.index}")
    print(f"Target label -> {label!r}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Item hover center -> x={item_point.x} y={item_point.y}")
    print(f"Coarse probes attempted -> {probes}")
    print(f"First action hit -> x={first_hit.point.x} y={first_hit.point.y}; signal={first_hit.signal}")
    print(f"Action node address -> 0x{first_hit.address:x}")
    print(f"button -> {first_hit.button!r}")
    print(f"func -> {first_hit.func!r}")
    print(f"id -> {first_hit.control_id!r}")
    print(f"Measured action hit bounds -> left={left} top={top} right={right} bottom={bottom}")
    print(f"Measured action center -> x={center.x} y={center.y}")
    print(f"Measured-center live hit-test -> {'PASS' if center_hit is not None else 'FAIL'}")
    if center_hit is not None:
        print(f"Measured-center hit signal -> {center_hit.signal}")
    return 0 if center_hit is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
