from __future__ import annotations

import argparse
import time

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_shop_purchase_mouse import (
    resolve_live_buy_target,
    resolve_live_shop_item_target,
)
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


REQUIRED_GEOMETRY = ("x", "y", "w", "h")


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _fmt_geometry(value: dict[str, float]) -> str:
    if not value:
        return "missing"
    return " ".join(
        f"{name}={value[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in value
    )


def _hover_state(decoder, fields: dict) -> dict[str, object]:
    result: dict[str, object] = {}
    states = _table_fields(decoder, fields.get("states"))
    hover = _table_fields(decoder, states.get("hover"))
    for name, value in hover.items():
        primitive = _primitive(value)
        if primitive is not None:
            result[name] = primitive
    return result


def _describe_node(decoder, label: str, value) -> tuple[int | None, object, object, object]:
    address = _table_address(value)
    if address is None:
        print(f"{label} -> missing")
        return None, None, None, None

    fields = _table_fields(decoder, value)
    config = _table_fields(decoder, fields.get("config"))
    button = _primitive(config.get("button"))
    func = _primitive(config.get("func"))
    control_id = _primitive(config.get("id"))
    print(f"{label} address -> 0x{address:x}")
    print(f"  button -> {button!r}")
    print(f"  func -> {func!r}")
    print(f"  id -> {control_id!r}")
    print(f"  T -> {_fmt_geometry(_geometry(decoder, fields.get('T')))}")
    print(f"  VT -> {_fmt_geometry(_geometry(decoder, fields.get('VT')))}")
    hover = _hover_state(decoder, fields)
    print(f"  states.hover -> {hover!r}")

    parent_value = fields.get("parent")
    parent_address = _table_address(parent_value)
    if parent_address is not None:
        parent = _table_fields(decoder, parent_value)
        parent_config = _table_fields(decoder, parent.get("config"))
        print(f"  parent address -> 0x{parent_address:x}")
        print(
            "  parent config -> "
            f"button={_primitive(parent_config.get('button'))!r}; "
            f"func={_primitive(parent_config.get('func'))!r}; "
            f"id={_primitive(parent_config.get('id'))!r}"
        )
        print(f"  parent T -> {_fmt_geometry(_geometry(decoder, parent.get('T')))}")
        print(f"  parent VT -> {_fmt_geometry(_geometry(decoder, parent.get('VT')))}")

    return address, button, func, control_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Hover one live main-shop item, resolve its ordinary Buy center, then move "
            "the normal Windows cursor to that center and inspect Balatro's live cursor "
            "target. No mouse click is sent."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--card-settle", type=float, default=0.40)
    parser.add_argument("--buy-settle", type=float, default=0.40)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")
    if args.card_settle < 0 or args.buy_settle < 0:
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
            mouse.move_screen(buy.screen_center)
            if args.buy_settle:
                time.sleep(args.buy_settle)

            decoder, _, root = observer._root()
            controller = _table_fields(decoder, root.get("CONTROLLER"))
            cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
            target_value = cursor_hover.get("target")
            prev_target_value = cursor_hover.get("prev_target")
            node_value = cursor_hover.get("node")

            primitives: dict[str, object] = {}
            for name, value in cursor_hover.items():
                primitive = _primitive(value)
                if primitive is not None:
                    primitives[name] = primitive
    except Exception as error:
        print("Live SHOP Buy hover validation -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse movement sent -> False or incomplete")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live SHOP Buy hover validation -> DIAGNOSTIC")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Target index -> {item.index}")
    print(f"Target label -> {item.label!r}")
    print(f"Item hover center -> x={item.screen_center.x} y={item.screen_center.y}")
    print(f"Computed Buy center -> x={buy.screen_center.x} y={buy.screen_center.y}")
    print(f"Buy geometry source -> {buy.geometry_source}")
    print(f"Buy geometry -> {_fmt_geometry(buy.geometry)}")
    print(f"cursor_hover primitives -> {primitives!r}")

    _, target_button, target_func, _ = _describe_node(
        decoder, "cursor_hover.target", target_value
    )
    _, prev_button, prev_func, _ = _describe_node(
        decoder, "cursor_hover.prev_target", prev_target_value
    )
    _describe_node(decoder, "cursor_hover.node", node_value)

    buy_hit = (
        (target_button == "buy_from_shop" and target_func == "can_buy")
        or (prev_button == "buy_from_shop" and prev_func == "can_buy")
    )
    print(f"Computed Buy center live hit-test -> {'PASS' if buy_hit else 'FAIL'}")
    return 0 if buy_hit else 1


if __name__ == "__main__":
    raise SystemExit(main())
