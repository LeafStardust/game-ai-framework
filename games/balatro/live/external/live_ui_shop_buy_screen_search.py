from __future__ import annotations

import argparse
import time

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _number,
    _primitive,
    _table_fields,
)
from .live_shop_purchase_mouse import (
    resolve_live_buy_target,
    resolve_live_shop_item_target,
)
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator


EXPECTED_BUTTON = "buy_from_shop"
EXPECTED_FUNC = "can_buy"


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _active_hover(decoder, fields: dict) -> bool:
    direct = _primitive(fields.get("hover"))
    if direct is True:
        return True

    states = _table_fields(decoder, fields.get("states"))
    hover = _table_fields(decoder, states.get("hover"))
    return _primitive(hover.get("is")) is True


def _node_is_buy(decoder, value, *, expected_addresses: set[int]) -> bool:
    address = _table_address(value)
    seen: set[int] = set()
    depth = 0
    while address is not None and address not in seen and depth < 12:
        if address in expected_addresses:
            return True
        seen.add(address)
        fields = decoder.string_fields(address)
        config = _table_fields(decoder, fields.get("config"))
        if (
            _primitive(config.get("button")) == EXPECTED_BUTTON
            and _primitive(config.get("func")) == EXPECTED_FUNC
        ):
            return True
        address = _table_address(fields.get("parent"))
        depth += 1
    return False


def _point_hits_buy(
    observer: LiveMemoryBalatroObserver,
    mouse: BalatroMouseController,
    item_point: PixelPoint,
    probe_point: PixelPoint,
    *,
    card_settle: float,
    probe_settle: float,
    client_rect,
) -> tuple[bool, str]:
    # Re-enter the card before every probe so Balatro recreates/reattaches the
    # ephemeral purchase UI consistently.
    mouse.move_screen(item_point)
    if card_settle:
        time.sleep(card_settle)

    decoder, _, root = observer._root()
    buy = resolve_live_buy_target(decoder, root, client_rect)
    expected_addresses = {buy.container_address, buy.ui_root_address}

    mouse.move_screen(probe_point)
    if probe_settle:
        time.sleep(probe_settle)

    decoder, _, root = observer._root()

    # First inspect the exact UIRoot/container object addresses from the hover
    # just before the probe. If Balatro keeps them alive, states.hover.is is the
    # strongest hit signal available.
    direct_hits: list[str] = []
    for name, address in (
        ("UIRoot", buy.ui_root_address),
        ("container", buy.container_address),
    ):
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue
        if _active_hover(decoder, fields):
            direct_hits.append(name)

    if direct_hits:
        return True, "states.hover.is:" + ",".join(direct_hits)

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        value = cursor_hover.get(name)
        try:
            if _node_is_buy(
                decoder,
                value,
                expected_addresses=expected_addresses,
            ):
                return True, f"cursor_hover.{name}"
        except Exception:
            continue

    return False, ""


def _coarse_offsets(x_radius: int, y_radius: int, step: int) -> list[tuple[int, int]]:
    offsets = [
        (dx, dy)
        for dx in range(-x_radius, x_radius + 1, step)
        for dy in range(-y_radius, y_radius + 1, step)
    ]
    offsets.sort(key=lambda value: (abs(value[0]) + abs(value[1]), abs(value[1]), abs(value[0])))
    return offsets


def _scan_axis(
    observer,
    mouse,
    item_point,
    origin,
    *,
    axis: str,
    direction: int,
    fine_step: int,
    max_distance: int,
    card_settle: float,
    probe_settle: float,
    client_rect,
) -> int:
    last_hit = origin.x if axis == "x" else origin.y
    for distance in range(fine_step, max_distance + fine_step, fine_step):
        if axis == "x":
            point = PixelPoint(origin.x + direction * distance, origin.y)
        else:
            point = PixelPoint(origin.x, origin.y + direction * distance)
        hit, _ = _point_hits_buy(
            observer,
            mouse,
            item_point,
            point,
            card_settle=card_settle,
            probe_settle=probe_settle,
            client_rect=client_rect,
        )
        if not hit:
            break
        last_hit = point.x if axis == "x" else point.y
    return last_hit


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search screen pixels around Balatro's live-derived Buy geometry using only "
            "normal mouse movement and Balatro live hover state. No click is sent."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--x-radius", type=int, default=160)
    parser.add_argument("--y-radius", type=int, default=180)
    parser.add_argument("--coarse-step", type=int, default=20)
    parser.add_argument("--fine-step", type=int, default=4)
    parser.add_argument("--card-settle", type=float, default=0.10)
    parser.add_argument("--probe-settle", type=float, default=0.10)
    args = parser.parse_args()

    if args.index < 0:
        parser.error("--index cannot be negative")
    for name in ("x_radius", "y_radius", "coarse_step", "fine_step"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.card_settle < 0 or args.probe_settle < 0:
        parser.error("settle delays cannot be negative")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)

            snapshot = observer.observe()
            decoder, _, root = observer._root()
            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
                raise RuntimeError("missing positive G.TILE_W / G.TILE_H")

            item = resolve_live_shop_item_target(
                snapshot,
                index=args.index,
                logical_width=float(tile_w),
                logical_height=float(tile_h),
                client_rect=window.client_rect,
            )

            mouse.move_screen(item.screen_center)
            if args.card_settle:
                time.sleep(args.card_settle)
            decoder, _, root = observer._root()
            buy = resolve_live_buy_target(decoder, root, window.client_rect)
            guessed_center = buy.screen_center

            first_hit: PixelPoint | None = None
            first_reason = ""
            probes = 0
            for dx, dy in _coarse_offsets(
                args.x_radius,
                args.y_radius,
                args.coarse_step,
            ):
                point = PixelPoint(guessed_center.x + dx, guessed_center.y + dy)
                probes += 1
                hit, reason = _point_hits_buy(
                    observer,
                    mouse,
                    item.screen_center,
                    point,
                    card_settle=args.card_settle,
                    probe_settle=args.probe_settle,
                    client_rect=window.client_rect,
                )
                if hit:
                    first_hit = point
                    first_reason = reason
                    break

            if first_hit is None:
                print("Live SHOP Buy screen search -> INCONCLUSIVE")
                print("Observation source -> live Balatro process memory")
                print("Mouse movement sent -> True")
                print("Mouse clicks sent -> False")
                print("Process writes/injection -> False")
                print(f"Target label -> {item.label!r}")
                print(
                    "Nested-geometry guessed Buy center -> "
                    f"x={guessed_center.x} y={guessed_center.y}"
                )
                print(f"Coarse probes attempted -> {probes}")
                print("Buy hit region discovered -> False")
                return 1

            left = _scan_axis(
                observer,
                mouse,
                item.screen_center,
                first_hit,
                axis="x",
                direction=-1,
                fine_step=args.fine_step,
                max_distance=args.x_radius,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
                client_rect=window.client_rect,
            )
            right = _scan_axis(
                observer,
                mouse,
                item.screen_center,
                first_hit,
                axis="x",
                direction=1,
                fine_step=args.fine_step,
                max_distance=args.x_radius,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
                client_rect=window.client_rect,
            )
            top = _scan_axis(
                observer,
                mouse,
                item.screen_center,
                first_hit,
                axis="y",
                direction=-1,
                fine_step=args.fine_step,
                max_distance=args.y_radius,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
                client_rect=window.client_rect,
            )
            bottom = _scan_axis(
                observer,
                mouse,
                item.screen_center,
                first_hit,
                axis="y",
                direction=1,
                fine_step=args.fine_step,
                max_distance=args.y_radius,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
                client_rect=window.client_rect,
            )

            measured_center = PixelPoint(
                round((left + right) / 2),
                round((top + bottom) / 2),
            )

            center_hit, center_reason = _point_hits_buy(
                observer,
                mouse,
                item.screen_center,
                measured_center,
                card_settle=args.card_settle,
                probe_settle=args.probe_settle,
                client_rect=window.client_rect,
            )
    except Exception as error:
        print("Live SHOP Buy screen search -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live SHOP Buy screen search -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Target index -> {item.index}")
    print(f"Target label -> {item.label!r}")
    print(f"Item hover center -> x={item.screen_center.x} y={item.screen_center.y}")
    print(
        "Nested-geometry guessed Buy center -> "
        f"x={guessed_center.x} y={guessed_center.y}"
    )
    print(f"Coarse probes attempted -> {probes}")
    print(f"First Buy hit -> x={first_hit.x} y={first_hit.y}; via={first_reason}")
    print(f"Measured Buy hit bounds -> left={left} top={top} right={right} bottom={bottom}")
    print(f"Measured Buy center -> x={measured_center.x} y={measured_center.y}")
    print(f"Measured-center live hit-test -> {'PASS' if center_hit else 'FAIL'}")
    if center_reason:
        print(f"Measured-center hit signal -> {center_reason}")
    return 0 if center_hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
