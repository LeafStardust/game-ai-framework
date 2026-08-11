from __future__ import annotations

import time
from dataclasses import dataclass

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import LiveMemoryBalatroObserver, _primitive, _table_fields
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindow, BalatroWindowLocator


EXPECTED_BUTTON = "reroll_shop"
EXPECTED_FUNC = "can_reroll"
MAX_PARENT_DEPTH = 12


class LiveShopRerollMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveShopRerollTarget:
    screen_point: PixelPoint
    node_address: int
    button: str
    func: str
    control_id: object
    hit_signal: str
    probes: int


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _resolve_reroll_from_node(decoder, value, signal: str):
    address = _table_address(value)
    seen: set[int] = set()
    depth = 0
    while address is not None and address not in seen and depth < MAX_PARENT_DEPTH:
        seen.add(address)
        fields = decoder.string_fields(address)
        config = _table_fields(decoder, fields.get("config"))
        button = _primitive(config.get("button"))
        func = _primitive(config.get("func"))
        control_id = _primitive(config.get("id"))
        if button == EXPECTED_BUTTON and func == EXPECTED_FUNC:
            return address, button, func, control_id, f"{signal}.parent[{depth}]"
        address = _table_address(fields.get("parent"))
        depth += 1
    return None


def live_reroll_hit_test(observer: LiveMemoryBalatroObserver, point: PixelPoint):
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        try:
            resolved = _resolve_reroll_from_node(
                decoder,
                cursor_hover.get(name),
                f"cursor_hover.{name}",
            )
        except Exception:
            continue
        if resolved is not None:
            address, button, func, control_id, signal = resolved
            return LiveShopRerollTarget(
                screen_point=point,
                node_address=address,
                button=str(button),
                func=str(func),
                control_id=control_id,
                hit_signal=signal,
                probes=0,
            )
    return None


def _search_points(rect, step: int) -> list[PixelPoint]:
    left = rect.left + round(rect.width * 0.12)
    right = rect.left + round(rect.width * 0.88)
    top = rect.top + round(rect.height * 0.28)
    bottom = rect.top + round(rect.height * 0.88)
    points = [
        PixelPoint(x, y)
        for y in range(top, bottom + 1, step)
        for x in range(left, right + 1, step)
    ]
    cx = rect.left + rect.width // 2
    cy = rect.top + round(rect.height * 0.58)
    points.sort(key=lambda point: abs(point.x - cx) + abs(point.y - cy))
    return points


class LiveMemoryShopRerollMouseExecutor:
    """Reroll the SHOP using normal mouse input and live hover authorization."""

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        search_step: int = 40,
        probe_settle_delay: float = 0.06,
        click_settle_delay: float = 0.05,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.search_step = max(1, int(search_step))
        self.probe_settle_delay = max(0.0, probe_settle_delay)
        self.click_settle_delay = max(0.0, click_settle_delay)
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)
        self._owns_observer = observer is None

    def preview(self) -> tuple[LiveBalatroSnapshot, BalatroWindow]:
        window = self.window_locator.find()
        snapshot = self.observer.observe()
        if snapshot.phase != "SHOP":
            raise LiveShopRerollMouseError(
                f"Balatro is in {snapshot.phase}, expected SHOP"
            )
        return snapshot, window

    def dispatch(self) -> tuple[LiveBalatroSnapshot, LiveShopRerollTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        self._wait_for_foreground(window.handle)
        if self.focus_settle_delay:
            time.sleep(self.focus_settle_delay)
        window = self.window_locator.refresh(window.handle)

        before = self.observer.observe()
        if before.phase != "SHOP":
            raise LiveShopRerollMouseError(
                f"Balatro is in {before.phase}, expected SHOP"
            )

        target = None
        for probes, point in enumerate(_search_points(window.client_rect, self.search_step), start=1):
            self.mouse.move_screen(point)
            if self.probe_settle_delay:
                time.sleep(self.probe_settle_delay)
            hit = live_reroll_hit_test(self.observer, point)
            if hit is not None:
                target = LiveShopRerollTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                )
                break

        if target is None:
            raise LiveShopRerollMouseError("unable to locate live Reroll control")

        self.mouse.move_screen(target.screen_point)
        if self.click_settle_delay:
            time.sleep(self.click_settle_delay)
        confirmed = live_reroll_hit_test(self.observer, target.screen_point)
        if confirmed is None:
            raise LiveShopRerollMouseError(
                "verified Reroll point lost live hover before click"
            )

        self.mouse.click_screen(target.screen_point, hover_delay=0.0)
        return before, target

    def _wait_for_foreground(self, handle: int) -> None:
        foreground_handle = getattr(self.window_locator, "foreground_handle", None)
        if not callable(foreground_handle):
            return
        deadline = time.monotonic() + self.focus_timeout
        while True:
            if foreground_handle() == handle:
                return
            if time.monotonic() >= deadline:
                raise LiveShopRerollMouseError(
                    "Balatro did not become foreground before Reroll click"
                )
            if self.focus_poll_interval:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryShopRerollMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
