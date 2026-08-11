from __future__ import annotations

import time
from collections import deque
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
from .viewport import PixelPoint
from .window import BalatroWindowLocator

EXPECTED_BUTTON = "skip_booster"
EXPECTED_FUNC = "can_skip_booster"
MAX_PARENT_DEPTH = 12
MAX_MEMORY_DEPTH = 9
MAX_MEMORY_TABLES = 4000


class LivePackSkipMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LivePackSkipTarget:
    screen_point: PixelPoint
    node_address: int
    button: object
    func: object
    control_id: object
    hit_signal: str
    probes: int
    location_source: str


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _resolve_skip(decoder, value, signal: str):
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
        if button == EXPECTED_BUTTON and func == EXPECTED_FUNC:
            return address, button, func, control_id, f"{signal}.parent[{depth}]"
        address = _table_address(fields.get("parent"))
    return None


def _current_hit(observer: LiveMemoryBalatroObserver, point: PixelPoint):
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        resolved = _resolve_skip(
            decoder,
            cursor_hover.get(name),
            f"cursor_hover.{name}",
        )
        if resolved is not None:
            return resolved
    return None


def _memory_candidates(observer: LiveMemoryBalatroObserver, client_rect):
    decoder, _, root = observer._root()
    tile_w = _number(root.get("TILE_W"))
    tile_h = _number(root.get("TILE_H"))
    if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
        return []
    transform = BalatroLogicalViewport(float(tile_w), float(tile_h), client_rect)

    preferred_names = (
        "UIDEF",
        "UIT",
        "CONTROLLER",
        "booster_pack",
        "ROOM",
        "ROOM_ATTACH",
    )
    roots = []
    for name in preferred_names:
        value = root.get(name)
        address = _table_address(value)
        if address is not None:
            roots.append(address)

    queue = deque((address, 0) for address in roots)
    seen: set[int] = set()
    result: list[tuple[int, PixelPoint]] = []
    while queue and len(seen) < MAX_MEMORY_TABLES:
        address, depth = queue.popleft()
        if address in seen:
            continue
        seen.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue
        config = _table_fields(decoder, fields.get("config"))
        if (
            _primitive(config.get("button")) == EXPECTED_BUTTON
            and _primitive(config.get("func")) == EXPECTED_FUNC
        ):
            geometry = _geometry(decoder, fields.get("VT")) or _geometry(decoder, fields.get("T"))
            if all(name in geometry for name in ("x", "y", "w", "h")):
                result.append(
                    (
                        address,
                        transform.screen_point(
                            float(geometry["x"]) + float(geometry["w"]) / 2.0,
                            float(geometry["y"]) + float(geometry["h"]) / 2.0,
                        ),
                    )
                )
        if depth >= MAX_MEMORY_DEPTH:
            continue
        for value in fields.values():
            child = _table_address(value)
            if child is not None:
                queue.append((child, depth + 1))
        try:
            items = decoder.array_items(address)
        except Exception:
            items = []
        for _, value in items:
            child = _table_address(value)
            if child is not None:
                queue.append((child, depth + 1))

    unique = []
    used = set()
    for address, point in result:
        if address not in used:
            unique.append((address, point))
            used.add(address)
    return unique


def _fallback_points(rect, step: int) -> list[PixelPoint]:
    left = rect.left + round(rect.width * 0.08)
    right = rect.right - round(rect.width * 0.08)
    top = rect.top + round(rect.height * 0.18)
    bottom = rect.bottom - round(rect.height * 0.04)
    points = [
        PixelPoint(x, y)
        for y in range(top, bottom + 1, step)
        for x in range(left, right + 1, step)
    ]
    cx = rect.left + rect.width // 2
    cy = rect.top + round(rect.height * 0.78)
    points.sort(key=lambda point: abs(point.x - cx) + abs(point.y - cy))
    return points


class LivePackSkipMouseExecutor:
    """Skip the current booster pack with exact live control identity checks."""

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        probe_settle_delay: float = 0.06,
        fallback_step: int = 28,
        focus_settle_delay: float = 0.25,
        result_timeout: float = 8.0,
        poll_interval: float = 0.05,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.probe_settle_delay = max(0.0, probe_settle_delay)
        self.fallback_step = max(1, int(fallback_step))
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.result_timeout = max(0.0, result_timeout)
        self.poll_interval = max(0.0, poll_interval)
        self._owns_observer = observer is None

    def _probe(self, point: PixelPoint):
        self.mouse.move_screen(point)
        if self.probe_settle_delay:
            time.sleep(self.probe_settle_delay)
        return _current_hit(self.observer, point)

    def dispatch(self) -> tuple[str, str, LivePackSkipTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        if self.focus_settle_delay:
            time.sleep(self.focus_settle_delay)
        window = self.window_locator.refresh(window.handle)

        before = self.observer.observe()
        if not before.phase.endswith("_PACK"):
            raise LivePackSkipMouseError(
                f"Balatro is in {before.phase}, expected *_PACK"
            )

        target = None
        probes = 0
        for expected_address, point in _memory_candidates(self.observer, window.client_rect):
            probes += 1
            resolved = self._probe(point)
            if resolved is None or resolved[0] != expected_address:
                continue
            address, button, func, control_id, signal = resolved
            target = LivePackSkipTarget(
                point, address, button, func, control_id, signal, probes, "memory_geometry"
            )
            break

        if target is None:
            for point in _fallback_points(window.client_rect, self.fallback_step):
                probes += 1
                resolved = self._probe(point)
                if resolved is None:
                    continue
                address, button, func, control_id, signal = resolved
                target = LivePackSkipTarget(
                    point, address, button, func, control_id, signal, probes, "fallback_screen_search"
                )
                break

        if target is None:
            raise LivePackSkipMouseError("unable to locate live skip_booster/can_skip_booster control")

        self.mouse.move_screen(target.screen_point)
        if self.probe_settle_delay:
            time.sleep(self.probe_settle_delay)
        resolved = _current_hit(self.observer, target.screen_point)
        if resolved is None or resolved[0] != target.node_address:
            raise LivePackSkipMouseError("verified pack Skip point lost live identity before click")
        self.mouse.click_screen(target.screen_point, hover_delay=0.0)

        deadline = time.monotonic() + self.result_timeout
        phase_after = before.phase
        while True:
            after = self.observer.observe()
            phase_after = after.phase
            if phase_after != before.phase:
                break
            if time.monotonic() >= deadline:
                raise LivePackSkipMouseError("timed out waiting for booster pack Skip transition")
            if self.poll_interval:
                time.sleep(self.poll_interval)

        return before.phase, phase_after, target

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LivePackSkipMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
