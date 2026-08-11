from __future__ import annotations

import time
from dataclasses import dataclass

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindow, BalatroWindowLocator, WindowRect


EXPECTED_BUTTON = "toggle_shop"
EXPECTED_ID = "next_round_button"
REQUIRED_GEOMETRY = ("x", "y", "w", "h")


class LiveShopNextRoundMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveShopNextRoundTarget:
    node_address: int
    button: str
    control_id: str
    geometry_source: str
    geometry: dict[str, float]
    screen_center: PixelPoint


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _complete_geometry(value: dict[str, float]) -> bool:
    return all(name in value for name in REQUIRED_GEOMETRY)


def resolve_live_next_round_target(
    decoder,
    root: dict,
    client_rect: WindowRect,
) -> LiveShopNextRoundTarget:
    """Resolve the visible SHOP Next Round control from live UI memory.

    This follows Balatro's public controller snap target only. It performs no
    process writes, callback invocation, deck traversal, or RNG inspection.
    """

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    if not controller:
        raise LiveShopNextRoundMouseError(
            "G.CONTROLLER is unavailable or not a table"
        )

    snap_cursor_to = _table_fields(decoder, controller.get("snap_cursor_to"))
    if not snap_cursor_to:
        raise LiveShopNextRoundMouseError(
            "G.CONTROLLER.snap_cursor_to is unavailable or not a table"
        )

    node_value = snap_cursor_to.get("node")
    node_address = _table_address(node_value)
    if node_address is None:
        raise LiveShopNextRoundMouseError(
            "G.CONTROLLER.snap_cursor_to.node is unavailable or not a table"
        )

    node = _table_fields(decoder, node_value)
    if not node:
        raise LiveShopNextRoundMouseError("unable to read Next Round owner node")

    config = _table_fields(decoder, node.get("config"))
    button = _primitive(config.get("button"))
    control_id = _primitive(config.get("id"))
    if button != EXPECTED_BUTTON or control_id != EXPECTED_ID:
        raise LiveShopNextRoundMouseError(
            "snap cursor node is not the Next Round control: "
            f"button={button!r}, id={control_id!r}"
        )

    node_vt = _geometry(decoder, node.get("VT"))
    node_t = _geometry(decoder, node.get("T"))
    if _complete_geometry(node_vt):
        geometry_source = "VT"
        geometry = node_vt
    elif _complete_geometry(node_t):
        geometry_source = "T"
        geometry = node_t
    else:
        raise LiveShopNextRoundMouseError(
            "Next Round node has no complete VT/T geometry"
        )

    tile_w = _number(root.get("TILE_W"))
    tile_h = _number(root.get("TILE_H"))
    if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
        raise LiveShopNextRoundMouseError("missing positive G.TILE_W / G.TILE_H")

    transform = BalatroLogicalViewport(float(tile_w), float(tile_h), client_rect)
    center = transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )
    return LiveShopNextRoundTarget(
        node_address=node_address,
        button=str(button),
        control_id=str(control_id),
        geometry_source=geometry_source,
        geometry=dict(geometry),
        screen_center=center,
    )


class LiveMemoryShopNextRoundMouseExecutor:
    """Click Next Round using live UI geometry and normal desktop mouse input."""

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)
        self._owns_observer = observer is None

    def preview(
        self,
    ) -> tuple[LiveBalatroSnapshot, LiveShopNextRoundTarget, BalatroWindow]:
        window = self.window_locator.find()
        snapshot = self.observer.observe()
        if snapshot.phase != "SHOP":
            raise LiveShopNextRoundMouseError(
                f"Balatro is in {snapshot.phase}, expected SHOP"
            )
        decoder, _, root = self.observer._root()
        target = resolve_live_next_round_target(
            decoder,
            root,
            window.client_rect,
        )
        return snapshot, target, window

    def dispatch(
        self,
    ) -> tuple[LiveBalatroSnapshot, LiveShopNextRoundTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        self._wait_for_foreground(window.handle)
        if self.focus_settle_delay > 0:
            time.sleep(self.focus_settle_delay)

        snapshot = self.observer.observe()
        if snapshot.phase != "SHOP":
            raise LiveShopNextRoundMouseError(
                f"Balatro is in {snapshot.phase}, expected SHOP"
            )

        decoder, _, root = self.observer._root()
        target = resolve_live_next_round_target(
            decoder,
            root,
            window.client_rect,
        )
        self.mouse.click_screen(target.screen_center)
        return snapshot, target

    def _wait_for_foreground(self, handle: int) -> None:
        foreground_handle = getattr(self.window_locator, "foreground_handle", None)
        if not callable(foreground_handle):
            return

        deadline = time.monotonic() + self.focus_timeout
        while True:
            if foreground_handle() == handle:
                return
            if time.monotonic() >= deadline:
                raise LiveShopNextRoundMouseError(
                    "Balatro did not become foreground before Next Round click"
                )
            if self.focus_poll_interval > 0:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryShopNextRoundMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
