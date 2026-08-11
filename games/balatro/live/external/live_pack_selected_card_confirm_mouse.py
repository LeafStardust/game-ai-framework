from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator

EXPECTED_BUTTON = "use_card"
EXPECTED_FUNC = "can_select_card"
MAX_PARENT_DEPTH = 12
MAX_MEMORY_DEPTH = 9
MAX_MEMORY_TABLES = 5000
REQUIRED_GEOMETRY = ("x", "y", "w", "h")
MEMORY_ROOT_HINTS = (
    "ui",
    "pack",
    "booster",
    "button",
    "controller",
    "room",
)
MEMORY_SKIP_ROOTS = {
    "GAME",
    "deck",
    "playing_cards",
    "pseudorandom",
    "pseudoseed",
}


class LivePackSelectedCardConfirmError(RuntimeError):
    pass


@dataclass(frozen=True)
class LivePackSelectedCard:
    address: int


@dataclass(frozen=True)
class LivePackConfirmTarget:
    screen_point: PixelPoint
    node_address: int
    button: object
    func: object
    control_id: object
    hit_signal: str
    probes: int
    location_source: str
    memory_candidates: int
    used_local_search: bool
    used_fallback_search: bool


@dataclass(frozen=True)
class _MemoryConfirmCandidate:
    node_address: int
    geometry: dict[str, float]
    geometry_source: str


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _complete_geometry(value: dict[str, float]) -> bool:
    return all(name in value for name in REQUIRED_GEOMETRY)


def _highlighted_card(observer: LiveMemoryBalatroObserver) -> LivePackSelectedCard:
    decoder, _, root = observer._root()
    area = _table_fields(decoder, root.get("pack_cards"))
    highlighted = [
        address for _, address in _array_table_values(decoder, area.get("highlighted"))
    ]
    if len(highlighted) != 1:
        raise LivePackSelectedCardConfirmError(
            f"expected exactly one highlighted pack card, found {len(highlighted)}"
        )
    return LivePackSelectedCard(highlighted[0])


def pack_contains_card(observer: LiveMemoryBalatroObserver, address: int) -> bool:
    try:
        decoder, _, root = observer._root()
        area = _table_fields(decoder, root.get("pack_cards"))
        cards = [
            card_address
            for _, card_address in _array_table_values(decoder, area.get("cards"))
        ]
        return address in cards
    except Exception:
        return False


def _resolve_confirm(decoder, value, signal: str):
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


def live_confirm_hit_test(
    observer: LiveMemoryBalatroObserver,
    point: PixelPoint,
) -> LivePackConfirmTarget | None:
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        resolved = _resolve_confirm(
            decoder,
            cursor_hover.get(name),
            f"cursor_hover.{name}",
        )
        if resolved is not None:
            address, button, func, control_id, signal = resolved
            return LivePackConfirmTarget(
                screen_point=point,
                node_address=address,
                button=button,
                func=func,
                control_id=control_id,
                hit_signal=signal,
                probes=0,
                location_source="live_hover",
                memory_candidates=0,
                used_local_search=False,
                used_fallback_search=False,
            )
    return None


def _memory_root_candidates(root: dict) -> list[tuple[str, int]]:
    preferred: list[tuple[str, int]] = []
    fallback: list[tuple[str, int]] = []
    for name, value in sorted(root.items()):
        if name in MEMORY_SKIP_ROOTS or value.kind != "table":
            continue
        entry = (name, int(value.value))
        fallback.append(entry)
        if any(token in name.casefold() for token in MEMORY_ROOT_HINTS):
            preferred.append(entry)
    return preferred or fallback


def _memory_confirm_candidates(
    observer: LiveMemoryBalatroObserver,
) -> tuple[list[_MemoryConfirmCandidate], float, float]:
    decoder, _, root = observer._root()
    tile_w = _number(root.get("TILE_W"))
    tile_h = _number(root.get("TILE_H"))
    if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
        raise LivePackSelectedCardConfirmError("missing positive G.TILE_W / G.TILE_H")

    queue = deque(
        (f"G.{name}", address, 0)
        for name, address in _memory_root_candidates(root)
    )
    visited: set[int] = set()
    found: list[_MemoryConfirmCandidate] = []

    while queue and len(visited) < MAX_MEMORY_TABLES:
        path, address, depth = queue.popleft()
        del path
        if address in visited:
            continue
        visited.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue

        config = _table_fields(decoder, fields.get("config"))
        button = _primitive(config.get("button"))
        func = _primitive(config.get("func"))
        if button == EXPECTED_BUTTON and func == EXPECTED_FUNC:
            vt = _geometry(decoder, fields.get("VT"))
            t = _geometry(decoder, fields.get("T"))
            if _complete_geometry(vt):
                found.append(_MemoryConfirmCandidate(address, vt, "VT"))
            elif _complete_geometry(t):
                found.append(_MemoryConfirmCandidate(address, t, "T"))

        if depth >= MAX_MEMORY_DEPTH:
            continue

        for name, value in fields.items():
            if value.kind == "table":
                queue.append((name, int(value.value), depth + 1))
        try:
            array_items = decoder.array_items(address)
        except Exception:
            array_items = []
        for index, value in array_items:
            if value.kind == "table":
                queue.append((f"[{index}]", int(value.value), depth + 1))

    # Prefer unique config nodes. The same table can be reachable from several roots.
    unique: list[_MemoryConfirmCandidate] = []
    seen_addresses: set[int] = set()
    for candidate in found:
        if candidate.node_address in seen_addresses:
            continue
        seen_addresses.add(candidate.node_address)
        unique.append(candidate)
    return unique, float(tile_w), float(tile_h)


def _candidate_screen_point(
    candidate: _MemoryConfirmCandidate,
    *,
    logical_width: float,
    logical_height: float,
    client_rect,
) -> PixelPoint:
    transform = BalatroLogicalViewport(logical_width, logical_height, client_rect)
    geometry = candidate.geometry
    return transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )


def _inside_client(point: PixelPoint, rect) -> bool:
    return rect.left <= point.x < rect.right and rect.top <= point.y < rect.bottom


def _local_search_points(
    origin: PixelPoint,
    rect,
    *,
    step: int,
    radius_x: int,
    radius_y: int,
) -> list[PixelPoint]:
    points: list[PixelPoint] = []
    for dy in range(-radius_y, radius_y + 1, step):
        for dx in range(-radius_x, radius_x + 1, step):
            if dx == 0 and dy == 0:
                continue
            point = PixelPoint(origin.x + dx, origin.y + dy)
            if _inside_client(point, rect):
                points.append(point)
    points.sort(key=lambda point: abs(point.x - origin.x) + abs(point.y - origin.y))
    return points


def _search_points(rect, step: int) -> list[PixelPoint]:
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
    points.sort(key=lambda point: abs(point.x - cx) + abs(point.y - cy))
    return points


class LivePackSelectedCardConfirmExecutor:
    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        search_step: int = 24,
        local_search_step: int = 12,
        local_radius_x: int = 168,
        local_radius_y: int = 132,
        probe_settle_delay: float = 0.06,
        click_settle_delay: float = 0.05,
        focus_settle_delay: float = 0.25,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.search_step = max(1, int(search_step))
        self.local_search_step = max(1, int(local_search_step))
        self.local_radius_x = max(0, int(local_radius_x))
        self.local_radius_y = max(0, int(local_radius_y))
        self.probe_settle_delay = max(0.0, probe_settle_delay)
        self.click_settle_delay = max(0.0, click_settle_delay)
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self._owns_observer = observer is None

    def preview(self) -> tuple[LiveBalatroSnapshot, LivePackSelectedCard]:
        snapshot = self.observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            raise LivePackSelectedCardConfirmError(
                f"Balatro is in {snapshot.phase}, expected *_PACK"
            )
        return snapshot, _highlighted_card(self.observer)

    def _probe_point(self, point: PixelPoint):
        self.mouse.move_screen(point)
        if self.probe_settle_delay:
            time.sleep(self.probe_settle_delay)
        return live_confirm_hit_test(self.observer, point)

    def dispatch(
        self,
    ) -> tuple[LiveBalatroSnapshot, LivePackSelectedCard, LivePackConfirmTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        if self.focus_settle_delay:
            time.sleep(self.focus_settle_delay)
        window = self.window_locator.refresh(window.handle)

        before = self.observer.observe()
        if not before.phase.endswith("_PACK"):
            raise LivePackSelectedCardConfirmError(
                f"Balatro is in {before.phase}, expected *_PACK"
            )
        selected = _highlighted_card(self.observer)

        memory_candidates, tile_w, tile_h = _memory_confirm_candidates(self.observer)
        target = None
        probes = 0

        # Fast path: derive candidate points from exact live UI nodes in memory. The
        # nested T/VT center is only a guess: authorize it with live hover identity.
        for candidate in memory_candidates:
            origin = _candidate_screen_point(
                candidate,
                logical_width=tile_w,
                logical_height=tile_h,
                client_rect=window.client_rect,
            )
            if not _inside_client(origin, window.client_rect):
                continue

            probes += 1
            hit = self._probe_point(origin)
            if hit is not None and hit.node_address == candidate.node_address:
                target = LivePackConfirmTarget(
                    screen_point=origin,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    location_source=f"memory_{candidate.geometry_source}",
                    memory_candidates=len(memory_candidates),
                    used_local_search=False,
                    used_fallback_search=False,
                )
                break

            # Nested UI geometry is not always the literal clickable screen region.
            # Search only around that live-memory-derived guess before considering a
            # whole-client fallback. No offset is persisted or learned.
            for point in _local_search_points(
                origin,
                window.client_rect,
                step=self.local_search_step,
                radius_x=self.local_radius_x,
                radius_y=self.local_radius_y,
            ):
                probes += 1
                hit = self._probe_point(point)
                if hit is None or hit.node_address != candidate.node_address:
                    continue
                target = LivePackConfirmTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    location_source=f"memory_{candidate.geometry_source}_local_search",
                    memory_candidates=len(memory_candidates),
                    used_local_search=True,
                    used_fallback_search=False,
                )
                break
            if target is not None:
                break

        # Last-resort fail-safe for layouts whose memory geometry is too detached from
        # the real hit region. This is not the normal production path.
        if target is None:
            for point in _search_points(window.client_rect, self.search_step):
                probes += 1
                hit = self._probe_point(point)
                if hit is None:
                    continue
                target = LivePackConfirmTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    location_source="fallback_screen_search",
                    memory_candidates=len(memory_candidates),
                    used_local_search=False,
                    used_fallback_search=True,
                )
                break

        if target is None:
            raise LivePackSelectedCardConfirmError(
                "unable to locate live use_card/can_select_card control"
            )

        self.mouse.move_screen(target.screen_point)
        if self.click_settle_delay:
            time.sleep(self.click_settle_delay)
        confirmed = live_confirm_hit_test(self.observer, target.screen_point)
        if confirmed is None or confirmed.node_address != target.node_address:
            raise LivePackSelectedCardConfirmError(
                "verified pack confirm point lost live identity before click"
            )

        # Ensure the same single highlighted card still exists immediately before click.
        latest_selected = _highlighted_card(self.observer)
        if latest_selected.address != selected.address:
            raise LivePackSelectedCardConfirmError(
                "highlighted pack card changed before confirm click"
            )

        self.mouse.click_screen(target.screen_point, hover_delay=0.0)
        return before, selected, target

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LivePackSelectedCardConfirmExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
