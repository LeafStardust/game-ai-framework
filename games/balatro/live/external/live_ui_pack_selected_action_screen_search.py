from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from .live_memory_observer import LiveMemoryBalatroObserver, _array_table_values, _primitive, _table_fields
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator

MAX_PARENT_DEPTH = 12
SKIP_BUTTON = "skip_booster"
SKIP_FUNC = "can_skip_booster"


@dataclass(frozen=True)
class ControlHit:
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


def _pack_highlighted(decoder, root: dict) -> list[int]:
    area = _table_fields(decoder, root.get("pack_cards"))
    return [address for _, address in _array_table_values(decoder, area.get("highlighted"))]


def _resolve_control(decoder, value, signal: str):
    address = _table_address(value)
    seen: set[int] = set()
    for depth in range(MAX_PARENT_DEPTH):
        if address is None or address in seen:
            return None
        seen.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            return None
        config = _table_fields(decoder, fields.get("config"))
        button = _primitive(config.get("button"))
        func = _primitive(config.get("func"))
        control_id = _primitive(config.get("id"))
        if button is not None or func is not None or control_id is not None:
            if not (button == SKIP_BUTTON and func == SKIP_FUNC):
                return address, button, func, control_id, f"{signal}.parent[{depth}]"
        address = _table_address(fields.get("parent"))
    return None


def _current_hit(observer, point: PixelPoint) -> ControlHit | None:
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        resolved = _resolve_control(decoder, cursor_hover.get(name), f"cursor_hover.{name}")
        if resolved is not None:
            address, button, func, control_id, signal = resolved
            return ControlHit(point, signal, address, button, func, control_id)
    return None


def _probe(observer, mouse, point: PixelPoint, settle: float):
    mouse.move_screen(point)
    if settle:
        time.sleep(settle)
    return _current_hit(observer, point)


def _coarse_points(rect, step: int) -> list[PixelPoint]:
    left = rect.left + round(rect.width * 0.06)
    right = rect.right - round(rect.width * 0.06)
    top = rect.top + round(rect.height * 0.16)
    bottom = rect.bottom - round(rect.height * 0.04)
    points = [
        PixelPoint(x, y)
        for y in range(top, bottom + 1, step)
        for x in range(left, right + 1, step)
    ]
    cx = rect.left + rect.width // 2
    cy = rect.top + round(rect.height * 0.76)
    points.sort(key=lambda p: abs(p.x - cx) + abs(p.y - cy))
    return points


def _scan_edge(observer, mouse, origin, *, axis, direction, step, max_distance, settle):
    last = origin.x if axis == "x" else origin.y
    for distance in range(step, max_distance + step, step):
        point = (
            PixelPoint(origin.x + direction * distance, origin.y)
            if axis == "x"
            else PixelPoint(origin.x, origin.y + direction * distance)
        )
        if _probe(observer, mouse, point, settle) is None:
            break
        last = point.x if axis == "x" else point.y
    return last


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Locate any non-Skip actionable UI control while a pack card is highlighted. "
            "Uses normal cursor movement and live cursor-hover identity only; no click is sent."
        )
    )
    parser.add_argument("--coarse-step", type=int, default=24)
    parser.add_argument("--fine-step", type=int, default=4)
    parser.add_argument("--settle", type=float, default=0.06)
    args = parser.parse_args()
    if args.coarse_step <= 0 or args.fine_step <= 0:
        parser.error("scan steps must be positive")
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
            highlighted = _pack_highlighted(decoder, root)
            if len(highlighted) != 1:
                raise RuntimeError(
                    f"expected exactly one highlighted pack card, found {len(highlighted)}"
                )

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)

            first_hit = None
            probes = 0
            for point in _coarse_points(window.client_rect, args.coarse_step):
                probes += 1
                first_hit = _probe(observer, mouse, point, args.settle)
                if first_hit is not None:
                    break

            if first_hit is None:
                print("Live selected-pack action screen search -> INCONCLUSIVE")
                print("Observation source -> live Balatro process memory")
                print(f"Phase -> {snapshot.phase}")
                print(f"Highlighted card address -> 0x{highlighted[0]:x}")
                print("Mouse movement sent -> True")
                print("Mouse clicks sent -> False")
                print(f"Coarse probes attempted -> {probes}")
                return 1

            origin = first_hit.point
            left = _scan_edge(observer, mouse, origin, axis="x", direction=-1, step=args.fine_step, max_distance=220, settle=args.settle)
            right = _scan_edge(observer, mouse, origin, axis="x", direction=1, step=args.fine_step, max_distance=220, settle=args.settle)
            top = _scan_edge(observer, mouse, origin, axis="y", direction=-1, step=args.fine_step, max_distance=160, settle=args.settle)
            bottom = _scan_edge(observer, mouse, origin, axis="y", direction=1, step=args.fine_step, max_distance=160, settle=args.settle)
            center = PixelPoint(round((left + right) / 2), round((top + bottom) / 2))
            center_hit = _probe(observer, mouse, center, args.settle)
    except Exception as error:
        print("Live selected-pack action screen search -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live selected-pack action screen search -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print(f"Highlighted card address -> 0x{highlighted[0]:x}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
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
        print(f"Measured-center button -> {center_hit.button!r}")
        print(f"Measured-center func -> {center_hit.func!r}")
        print(f"Measured-center id -> {center_hit.control_id!r}")
    return 0 if center_hit is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
