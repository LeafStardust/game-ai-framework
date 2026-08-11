from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _primitive,
    _table_fields,
)
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator


REROLL_TOKENS = ("reroll", "reroll_shop")
MAX_PARENT_DEPTH = 12


@dataclass(frozen=True)
class RerollHit:
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


def _reroll_identity(config: dict) -> tuple[bool, object, object, object]:
    button = _primitive(config.get("button"))
    func = _primitive(config.get("func"))
    control_id = _primitive(config.get("id"))
    values = (button, func, control_id)
    matched = any(
        any(token in str(value).casefold() for token in REROLL_TOKENS)
        for value in values
        if value is not None
    )
    return matched, button, func, control_id


def _resolve_reroll_from_node(decoder, value, signal: str) -> RerollHit | None:
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
        matched, button, func, control_id = _reroll_identity(config)
        if matched:
            return RerollHit(
                point=PixelPoint(0, 0),
                signal=f"{signal}.parent[{depth}]",
                address=address,
                button=button,
                func=func,
                control_id=control_id,
            )
        address = _table_address(fields.get("parent"))
        depth += 1
    return None


def _current_reroll_hit(observer, point: PixelPoint) -> RerollHit | None:
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))

    for name in ("target", "prev_target", "node"):
        hit = _resolve_reroll_from_node(
            decoder,
            cursor_hover.get(name),
            f"cursor_hover.{name}",
        )
        if hit is not None:
            return RerollHit(
                point=point,
                signal=hit.signal,
                address=hit.address,
                button=hit.button,
                func=hit.func,
                control_id=hit.control_id,
            )
    return None


def _probe(observer, mouse, point: PixelPoint, settle: float) -> RerollHit | None:
    mouse.move_screen(point)
    if settle:
        time.sleep(settle)
    return _current_reroll_hit(observer, point)


def _coarse_points(rect, step: int) -> list[PixelPoint]:
    # The SHOP controls and offers occupy the central/lower client area. Keep the
    # scan broad enough to include Next Round/Reroll without traversing the whole
    # desktop or the very top HUD.
    left = rect.left + round(rect.width * 0.12)
    right = rect.left + round(rect.width * 0.88)
    top = rect.top + round(rect.height * 0.28)
    bottom = rect.top + round(rect.height * 0.88)

    points = [
        PixelPoint(x, y)
        for y in range(top, bottom + 1, step)
        for x in range(left, right + 1, step)
    ]
    # Search near the lower-middle shop controls first, then expand naturally.
    cx = rect.left + rect.width // 2
    cy = rect.top + round(rect.height * 0.58)
    points.sort(key=lambda point: abs(point.x - cx) + abs(point.y - cy))
    return points


def _scan_edge(
    observer,
    mouse,
    origin: PixelPoint,
    *,
    axis: str,
    direction: int,
    step: int,
    max_distance: int,
    settle: float,
) -> int:
    last = origin.x if axis == "x" else origin.y
    for distance in range(step, max_distance + step, step):
        if axis == "x":
            point = PixelPoint(origin.x + direction * distance, origin.y)
        else:
            point = PixelPoint(origin.x, origin.y + direction * distance)
        if _probe(observer, mouse, point, settle) is None:
            break
        last = point.x if axis == "x" else point.y
    return last


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Locate Balatro's live SHOP Reroll control using normal cursor movement "
            "and Balatro's own live cursor-hover identity. No click is sent."
        )
    )
    parser.add_argument("--coarse-step", type=int, default=40)
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
            if snapshot.phase != "SHOP":
                raise RuntimeError(f"Balatro is in {snapshot.phase}, expected SHOP")

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)

            first_hit: RerollHit | None = None
            probes = 0
            for point in _coarse_points(window.client_rect, args.coarse_step):
                probes += 1
                first_hit = _probe(observer, mouse, point, args.settle)
                if first_hit is not None:
                    break

            if first_hit is None:
                print("Live SHOP Reroll screen search -> INCONCLUSIVE")
                print("Observation source -> live Balatro process memory")
                print("Mouse movement sent -> True")
                print("Mouse clicks sent -> False")
                print("Process writes/injection -> False")
                print(f"Coarse probes attempted -> {probes}")
                print("Reroll hit region discovered -> False")
                return 1

            origin = first_hit.point
            left = _scan_edge(
                observer,
                mouse,
                origin,
                axis="x",
                direction=-1,
                step=args.fine_step,
                max_distance=200,
                settle=args.settle,
            )
            right = _scan_edge(
                observer,
                mouse,
                origin,
                axis="x",
                direction=1,
                step=args.fine_step,
                max_distance=200,
                settle=args.settle,
            )
            top = _scan_edge(
                observer,
                mouse,
                origin,
                axis="y",
                direction=-1,
                step=args.fine_step,
                max_distance=140,
                settle=args.settle,
            )
            bottom = _scan_edge(
                observer,
                mouse,
                origin,
                axis="y",
                direction=1,
                step=args.fine_step,
                max_distance=140,
                settle=args.settle,
            )
            center = PixelPoint(round((left + right) / 2), round((top + bottom) / 2))
            center_hit = _probe(observer, mouse, center, args.settle)
    except Exception as error:
        print("Live SHOP Reroll screen search -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live SHOP Reroll screen search -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(
        "Balatro client rect -> "
        f"left={window.client_rect.left} top={window.client_rect.top} "
        f"width={window.client_rect.width} height={window.client_rect.height}"
    )
    print(f"Coarse probes attempted -> {probes}")
    print(
        "First Reroll hit -> "
        f"x={first_hit.point.x} y={first_hit.point.y}; signal={first_hit.signal}"
    )
    print(f"Reroll node address -> 0x{first_hit.address:x}")
    print(f"button -> {first_hit.button!r}")
    print(f"func -> {first_hit.func!r}")
    print(f"id -> {first_hit.control_id!r}")
    print(
        "Measured Reroll hit bounds -> "
        f"left={left} top={top} right={right} bottom={bottom}"
    )
    print(f"Measured Reroll center -> x={center.x} y={center.y}")
    print(f"Measured-center live hit-test -> {'PASS' if center_hit else 'FAIL'}")
    if center_hit is not None:
        print(f"Measured-center hit signal -> {center_hit.signal}")
    return 0 if center_hit is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
