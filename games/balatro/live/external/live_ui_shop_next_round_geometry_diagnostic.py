from __future__ import annotations

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .window import BalatroWindowLocator


CONTROL_PATH = "G.CONTROLLER.snap_cursor_to.node"
EXPECTED_BUTTON = "toggle_shop"
EXPECTED_ID = "next_round_button"
REQUIRED_GEOMETRY = ("x", "y", "w", "h")


def _fmt_geometry(value: dict[str, float]) -> str:
    if not value:
        return "missing"
    return " ".join(
        f"{key}={value[key]:.6f}"
        for key in ("x", "y", "w", "h", "r", "scale")
        if key in value
    )


def _complete_geometry(value: dict[str, float]) -> bool:
    return all(key in value for key in REQUIRED_GEOMETRY)


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def main() -> int:
    try:
        window = BalatroWindowLocator().find()
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            snapshot = observer.observe()

            controller = _table_fields(decoder, root.get("CONTROLLER"))
            if not controller:
                raise RuntimeError("G.CONTROLLER is unavailable or not a table")

            snap_cursor_to = _table_fields(decoder, controller.get("snap_cursor_to"))
            if not snap_cursor_to:
                raise RuntimeError(
                    "G.CONTROLLER.snap_cursor_to is unavailable or not a table"
                )

            node_value = snap_cursor_to.get("node")
            node_address = _table_address(node_value)
            if node_address is None:
                raise RuntimeError(
                    "G.CONTROLLER.snap_cursor_to.node is unavailable or not a table"
                )

            node = _table_fields(decoder, node_value)
            if not node:
                raise RuntimeError("unable to read Next Round owner node")

            config = _table_fields(decoder, node.get("config"))
            button = _primitive(config.get("button"))
            control_id = _primitive(config.get("id"))

            node_t = _geometry(decoder, node.get("T"))
            node_vt = _geometry(decoder, node.get("VT"))

            parent_value = node.get("parent")
            parent_address = _table_address(parent_value)
            parent = _table_fields(decoder, parent_value)
            parent_t = _geometry(decoder, parent.get("T"))
            parent_vt = _geometry(decoder, parent.get("VT"))

            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
    except Exception as error:
        print("Live SHOP Next Round geometry diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live SHOP Next Round geometry diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print(f"Control path -> {CONTROL_PATH}")
    print(f"Node address -> 0x{node_address:x}")
    print(f"button -> {button!r}")
    print(f"id -> {control_id!r}")
    print(f"T -> {_fmt_geometry(node_t)}")
    print(f"VT -> {_fmt_geometry(node_vt)}")

    if parent_address is None:
        print("Parent -> missing")
    else:
        print(f"Parent address -> 0x{parent_address:x}")
        print(f"Parent T -> {_fmt_geometry(parent_t)}")
        print(f"Parent VT -> {_fmt_geometry(parent_vt)}")

    if snapshot.phase != "SHOP":
        print("SHOP phase guard -> FAIL")
        return 1

    if button != EXPECTED_BUTTON or control_id != EXPECTED_ID:
        print("Next Round identity guard -> FAIL")
        print(
            "Expected -> "
            f"button={EXPECTED_BUTTON!r}; id={EXPECTED_ID!r}"
        )
        return 1

    print("Next Round identity guard -> PASS")

    if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
        print("Coordinate transform -> FAIL")
        print("Reason -> missing positive G.TILE_W / G.TILE_H")
        return 2

    rect = window.client_rect
    transform = BalatroLogicalViewport(float(tile_w), float(tile_h), rect)
    print(
        "Balatro client rect -> "
        f"left={rect.left} top={rect.top} width={rect.width} height={rect.height}"
    )
    print(f"G.TILE_W -> {tile_w}")
    print(f"G.TILE_H -> {tile_h}")
    print(f"Logical-to-client scale -> {transform.scale:.6f} px/unit")
    print(f"Letterbox padding -> x={transform.pad_x:.6f} y={transform.pad_y:.6f}")

    if _complete_geometry(node_vt):
        source = "VT"
        geometry = node_vt
    elif _complete_geometry(node_t):
        source = "T"
        geometry = node_t
    else:
        print("Next Round geometry readiness -> FAIL")
        print("Reason -> neither node.VT nor node.T contains x/y/w/h")
        return 1

    logical_x = float(geometry["x"])
    logical_y = float(geometry["y"])
    logical_w = float(geometry["w"])
    logical_h = float(geometry["h"])
    logical_center_x = logical_x + logical_w / 2.0
    logical_center_y = logical_y + logical_h / 2.0

    screen_rect = transform.screen_rect(
        x=logical_x,
        y=logical_y,
        w=logical_w,
        h=logical_h,
    )
    screen_center = transform.screen_point(logical_center_x, logical_center_y)

    print(f"Geometry source selected -> {source}")
    print(
        "Logical center -> "
        f"x={logical_center_x:.6f} y={logical_center_y:.6f}"
    )
    print(
        "Screen rect -> "
        f"left={screen_rect.left} top={screen_rect.top} "
        f"width={screen_rect.width} height={screen_rect.height}"
    )
    print(f"Screen center -> x={screen_center.x} y={screen_center.y}")
    print("Next Round geometry readiness -> PASS")
    print("Next Round click sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
