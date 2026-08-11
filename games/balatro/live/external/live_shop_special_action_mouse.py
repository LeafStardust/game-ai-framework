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
from .window import BalatroWindow, BalatroWindowLocator


AREA_PAYLOADS = {
    "vouchers": "shop_vouchers",
    "boosters": "shop_boosters",
}
AREA_ROOTS = {
    "vouchers": "shop_vouchers",
    "boosters": "shop_booster",
}
EXPECTED = {
    "vouchers": (None, "can_redeem"),
    "boosters": ("use_card", "can_open"),
}
# Stable Balatro logical-UI hit offsets from the selected special card center.
# These are logical coordinates, not pixels. Every predicted point must still
# pass the exact live hover identity before a click is authorized.
ACTION_OFFSETS = {
    "vouchers": (0.0, 1.07),
    "boosters": (0.0, 1.33),
}
MAX_PARENT_DEPTH = 12
MAX_ACTION_DEPTH = 7
MAX_ACTION_TABLES = 800
REQUIRED_GEOMETRY = ("x", "y", "w", "h")


class LiveShopSpecialActionMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveShopSpecialItemTarget:
    area: str
    index: int
    label: str | None
    live_id: object
    cost: float
    geometry: dict[str, float]
    screen_center: PixelPoint


@dataclass(frozen=True)
class LiveShopSpecialActionTarget:
    screen_point: PixelPoint
    node_address: int
    button: object
    func: object
    control_id: object
    hit_signal: str
    probes: int
    item_click_point: PixelPoint | None = None
    location_source: str = "live_hover"
    used_local_search: bool = False
    used_fallback_search: bool = False


@dataclass(frozen=True)
class _MemoryActionCandidate:
    node_address: int
    geometry: dict[str, float]
    geometry_source: str


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _complete_geometry(value: dict[str, float]) -> bool:
    return all(name in value for name in REQUIRED_GEOMETRY)


def _target_item(
    snapshot: LiveBalatroSnapshot,
    area: str,
    index: int,
    *,
    logical_width: float,
    logical_height: float,
    client_rect,
) -> LiveShopSpecialItemTarget:
    if snapshot.phase != "SHOP":
        raise LiveShopSpecialActionMouseError(
            f"Balatro is in {snapshot.phase}, expected SHOP"
        )
    if area not in AREA_PAYLOADS:
        raise LiveShopSpecialActionMouseError(f"unsupported special SHOP area: {area}")
    if index < 0:
        raise LiveShopSpecialActionMouseError("shop item index cannot be negative")

    cards = (snapshot.payload.get(AREA_PAYLOADS[area]) or {}).get("cards") or []
    matches = [
        card
        for position, card in enumerate(cards)
        if int(card.get("area_index", position)) == index
    ]
    if len(matches) != 1:
        raise LiveShopSpecialActionMouseError(
            f"expected exactly one visible {area} item at index {index}, found {len(matches)}"
        )

    card = matches[0]
    geometry = dict(card.get("ui") or {})
    if not _complete_geometry(geometry):
        raise LiveShopSpecialActionMouseError("target special SHOP item has no complete live geometry")

    cost_value = card.get("cost")
    if not isinstance(cost_value, (int, float)):
        raise LiveShopSpecialActionMouseError("target special SHOP item has no numeric live cost")
    cost = float(cost_value)
    money = snapshot.payload.get("money")
    if isinstance(money, (int, float)) and float(money) < cost:
        raise LiveShopSpecialActionMouseError(
            f"target {area} item is unaffordable: money={money}, cost={cost:g}"
        )

    transform = BalatroLogicalViewport(logical_width, logical_height, client_rect)
    return LiveShopSpecialItemTarget(
        area=area,
        index=index,
        label=card.get("label") or card.get("ability_name") or card.get("center"),
        live_id=card.get("live_id"),
        cost=cost,
        geometry=geometry,
        screen_center=transform.card_center(geometry),
    )


def _same_item(expected: LiveShopSpecialItemTarget, actual: LiveShopSpecialItemTarget) -> bool:
    if expected.live_id is not None and actual.live_id is not None:
        return expected.live_id == actual.live_id
    return expected.index == actual.index and expected.label == actual.label


def _live_item_address(observer: LiveMemoryBalatroObserver, area: str, index: int) -> int:
    decoder, _, root = observer._root()
    area_fields = _table_fields(decoder, root.get(AREA_ROOTS[area]))
    cards = [address for _, address in _array_table_values(decoder, area_fields.get("cards"))]
    if index < 0 or index >= len(cards):
        raise LiveShopSpecialActionMouseError(
            f"live {area} item index {index} out of range for {len(cards)} cards"
        )
    return cards[index]


def _resolve_expected_from_node(decoder, value, signal: str, area: str):
    expected_button, expected_func = EXPECTED[area]
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
        if func == expected_func and (expected_button is None or button == expected_button):
            return address, button, func, control_id, f"{signal}.parent[{depth}]"
        address = _table_address(fields.get("parent"))
    return None


def live_special_action_hit_test(
    observer: LiveMemoryBalatroObserver,
    point: PixelPoint,
    area: str,
) -> LiveShopSpecialActionTarget | None:
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
            return LiveShopSpecialActionTarget(
                screen_point=point,
                node_address=address,
                button=button,
                func=func,
                control_id=control_id,
                hit_signal=signal,
                probes=0,
            )
    return None


def _cursor_reaches_item(observer: LiveMemoryBalatroObserver, item_address: int) -> bool:
    decoder, _, root = observer._root()
    try:
        fields = decoder.string_fields(item_address)
        states = _table_fields(decoder, fields.get("states"))
        hover = _table_fields(decoder, states.get("hover"))
        if _primitive(hover.get("is")) is True:
            return True
    except Exception:
        pass

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        address = _table_address(cursor_hover.get(name))
        seen: set[int] = set()
        for _ in range(MAX_PARENT_DEPTH):
            if address is None or address in seen:
                break
            if address == item_address:
                return True
            seen.add(address)
            try:
                node = decoder.string_fields(address)
            except Exception:
                break
            address = _table_address(node.get("parent"))
    return False


def _matches_expected_config(decoder, fields: dict, area: str) -> tuple[bool, object, object, object]:
    config = _table_fields(decoder, fields.get("config"))
    button = _primitive(config.get("button"))
    func = _primitive(config.get("func"))
    control_id = _primitive(config.get("id"))
    expected_button, expected_func = EXPECTED[area]
    matched = func == expected_func and (expected_button is None or button == expected_button)
    return matched, button, func, control_id


def _memory_action_candidates(
    observer: LiveMemoryBalatroObserver,
    area: str,
    item_address: int,
) -> list[_MemoryActionCandidate]:
    decoder, _, root = observer._root()
    roots = [item_address]

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        address = _table_address(cursor_hover.get(name))
        if address is not None:
            roots.append(address)

    queue = deque((address, 0) for address in roots)
    visited: set[int] = set()
    found: list[_MemoryActionCandidate] = []

    while queue and len(visited) < MAX_ACTION_TABLES:
        address, depth = queue.popleft()
        if address in visited:
            continue
        visited.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue

        matched, _, _, _ = _matches_expected_config(decoder, fields, area)
        if matched:
            vt = _geometry(decoder, fields.get("VT"))
            t = _geometry(decoder, fields.get("T"))
            if _complete_geometry(vt):
                found.append(_MemoryActionCandidate(address, dict(vt), "VT"))
            elif _complete_geometry(t):
                found.append(_MemoryActionCandidate(address, dict(t), "T"))

        if depth >= MAX_ACTION_DEPTH:
            continue

        for name, value in fields.items():
            if name == "parent" or value.kind != "table":
                continue
            queue.append((int(value.value), depth + 1))
        try:
            array_items = decoder.array_items(address)
        except Exception:
            array_items = []
        for _, value in array_items:
            if value.kind == "table":
                queue.append((int(value.value), depth + 1))

    unique: list[_MemoryActionCandidate] = []
    seen: set[int] = set()
    for candidate in found:
        if candidate.node_address in seen:
            continue
        seen.add(candidate.node_address)
        unique.append(candidate)
    return unique


def _template_point(
    item: LiveShopSpecialItemTarget,
    area: str,
    *,
    logical_width: float,
    logical_height: float,
    client_rect,
) -> PixelPoint:
    dx, dy = ACTION_OFFSETS[area]
    geometry = item.geometry
    x = float(geometry["x"]) + float(geometry["w"]) / 2.0 + float(dx)
    y = float(geometry["y"]) + float(geometry["h"]) / 2.0 + float(dy)
    transform = BalatroLogicalViewport(logical_width, logical_height, client_rect)
    return transform.screen_point(x, y)


def _candidate_point(
    candidate: _MemoryActionCandidate,
    *,
    logical_width: float,
    logical_height: float,
    client_rect,
) -> PixelPoint:
    geometry = candidate.geometry
    transform = BalatroLogicalViewport(logical_width, logical_height, client_rect)
    return transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )


def _local_points(origin: PixelPoint, rect, *, step: int = 16, radius_x: int = 80, radius_y: int = 112) -> list[PixelPoint]:
    points = [
        PixelPoint(origin.x + dx, origin.y + dy)
        for dy in range(-radius_y, radius_y + 1, step)
        for dx in range(-radius_x, radius_x + 1, step)
        if (dx or dy)
        and rect.left <= origin.x + dx < rect.right
        and rect.top <= origin.y + dy < rect.bottom
    ]
    points.sort(key=lambda point: abs(point.x - origin.x) + abs(point.y - origin.y))
    return points


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
    points.sort(key=lambda point: abs(point.x - item_point.x) + abs(point.y - item_point.y))
    return points


class LiveMemoryShopSpecialActionMouseExecutor:
    """Redeem a voucher or open a booster with the real two-click SHOP flow.

    Sequence:
      1. Click the exact live voucher/booster card.
      2. Resolve the generated Redeem/Open control from the selected card's live UI.
      3. Try the card-relative logical template, then direct live control geometry.
      4. Require the exact Balatro hover identity immediately before the action click.
      5. Click the generated action control once.

    Cursor searching is a fail-safe only; it is not the normal production path.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        search_step: int = 20,
        card_settle_delay: float = 0.10,
        probe_settle_delay: float = 0.08,
        click_settle_delay: float = 0.05,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.search_step = max(1, int(search_step))
        self.card_settle_delay = max(0.0, card_settle_delay)
        self.probe_settle_delay = max(0.0, probe_settle_delay)
        self.click_settle_delay = max(0.0, click_settle_delay)
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)
        self._owns_observer = observer is None

    def preview(self, area: str, index: int) -> tuple[LiveBalatroSnapshot, LiveShopSpecialItemTarget, BalatroWindow]:
        window = self.window_locator.find()
        snapshot = self.observer.observe()
        decoder, _, root = self.observer._root()
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
            raise LiveShopSpecialActionMouseError("missing positive G.TILE_W / G.TILE_H")
        target = _target_item(
            snapshot,
            area,
            index,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
            client_rect=window.client_rect,
        )
        return snapshot, target, window

    def _probe(self, point: PixelPoint, area: str):
        self.mouse.move_screen(point)
        if self.probe_settle_delay:
            time.sleep(self.probe_settle_delay)
        return live_special_action_hit_test(self.observer, point, area)

    def dispatch(
        self,
        area: str,
        index: int,
    ) -> tuple[LiveBalatroSnapshot, LiveShopSpecialItemTarget, LiveShopSpecialActionTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        self._wait_for_foreground(window.handle)
        if self.focus_settle_delay:
            time.sleep(self.focus_settle_delay)
        window = self.window_locator.refresh(window.handle)

        before = self.observer.observe()
        decoder, _, root = self.observer._root()
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
            raise LiveShopSpecialActionMouseError("missing positive G.TILE_W / G.TILE_H")
        logical_width = float(tile_w)
        logical_height = float(tile_h)
        item = _target_item(
            before,
            area,
            index,
            logical_width=logical_width,
            logical_height=logical_height,
            client_rect=window.client_rect,
        )
        item_address = _live_item_address(self.observer, area, index)

        # First required click: select/open the special SHOP card itself.
        self.mouse.move_screen(item.screen_center)
        if self.card_settle_delay:
            time.sleep(self.card_settle_delay)
        if not _cursor_reaches_item(self.observer, item_address):
            raise LiveShopSpecialActionMouseError(
                f"live cursor does not identify the requested {area} card before selection click"
            )
        self.mouse.click_screen(item.screen_center, hover_delay=0.0)
        if self.card_settle_delay:
            time.sleep(self.card_settle_delay)

        current = self.observer.observe()
        if current.phase != "SHOP":
            raise LiveShopSpecialActionMouseError(
                f"Balatro left SHOP after {area} card selection click: phase={current.phase}"
            )
        selected_item = _target_item(
            current,
            area,
            index,
            logical_width=logical_width,
            logical_height=logical_height,
            client_rect=window.client_rect,
        )
        if not _same_item(item, selected_item):
            raise LiveShopSpecialActionMouseError(
                f"{area} item identity changed after selection click"
            )
        fresh_address = _live_item_address(self.observer, area, index)
        if fresh_address != item_address:
            raise LiveShopSpecialActionMouseError(
                f"{area} live card address changed after selection click"
            )

        candidates = _memory_action_candidates(self.observer, area, item_address)
        if not candidates:
            raise LiveShopSpecialActionMouseError(
                f"{area} selection click did not expose the expected live action control"
            )
        candidate_addresses = {candidate.node_address for candidate in candidates}

        probes = 0
        target = None

        # Primary production path: stable card-relative logical template.
        template = _template_point(
            selected_item,
            area,
            logical_width=logical_width,
            logical_height=logical_height,
            client_rect=window.client_rect,
        )
        probes += 1
        hit = self._probe(template, area)
        if hit is not None and hit.node_address in candidate_addresses:
            target = LiveShopSpecialActionTarget(
                screen_point=template,
                node_address=hit.node_address,
                button=hit.button,
                func=hit.func,
                control_id=hit.control_id,
                hit_signal=hit.hit_signal,
                probes=probes,
                item_click_point=item.screen_center,
                location_source="special_card_template",
                used_local_search=False,
                used_fallback_search=False,
            )

        # Secondary path: use the generated control's own live VT/T center.
        if target is None:
            for candidate in candidates:
                point = _candidate_point(
                    candidate,
                    logical_width=logical_width,
                    logical_height=logical_height,
                    client_rect=window.client_rect,
                )
                probes += 1
                hit = self._probe(point, area)
                if hit is None or hit.node_address != candidate.node_address:
                    continue
                target = LiveShopSpecialActionTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    item_click_point=item.screen_center,
                    location_source=f"memory_{candidate.geometry_source}",
                    used_local_search=False,
                    used_fallback_search=True,
                )
                break

        # Bounded local search around the template only if both direct paths miss.
        if target is None:
            for point in _local_points(template, window.client_rect):
                probes += 1
                hit = self._probe(point, area)
                if hit is None or hit.node_address not in candidate_addresses:
                    continue
                target = LiveShopSpecialActionTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    item_click_point=item.screen_center,
                    location_source="special_card_template_local_search",
                    used_local_search=True,
                    used_fallback_search=True,
                )
                break

        # Absolute last resort: retain the old bounded cursor search for unknown UI
        # variants, but never use it unless the live-memory/template paths fail.
        if target is None:
            for point in _search_points(selected_item.screen_center, window.client_rect, self.search_step):
                probes += 1
                hit = self._probe(point, area)
                if hit is None or hit.node_address not in candidate_addresses:
                    continue
                target = LiveShopSpecialActionTarget(
                    screen_point=point,
                    node_address=hit.node_address,
                    button=hit.button,
                    func=hit.func,
                    control_id=hit.control_id,
                    hit_signal=hit.hit_signal,
                    probes=probes,
                    item_click_point=item.screen_center,
                    location_source="fallback_screen_search",
                    used_local_search=True,
                    used_fallback_search=True,
                )
                break

        if target is None:
            raise LiveShopSpecialActionMouseError(
                f"unable to locate live {area} action control after selection click"
            )

        self.mouse.move_screen(target.screen_point)
        if self.click_settle_delay:
            time.sleep(self.click_settle_delay)
        confirmed = live_special_action_hit_test(self.observer, target.screen_point, area)
        if confirmed is None or confirmed.node_address != target.node_address:
            raise LiveShopSpecialActionMouseError(
                f"verified {area} action point lost exact live identity before click"
            )
        if self.observer.observe().phase != "SHOP":
            raise LiveShopSpecialActionMouseError(
                f"Balatro left SHOP before {area} action click"
            )

        self.mouse.click_screen(target.screen_point, hover_delay=0.0)
        return before, selected_item, target

    def _wait_for_foreground(self, handle: int) -> None:
        foreground_handle = getattr(self.window_locator, "foreground_handle", None)
        if not callable(foreground_handle):
            return
        deadline = time.monotonic() + self.focus_timeout
        while True:
            if foreground_handle() == handle:
                return
            if time.monotonic() >= deadline:
                raise LiveShopSpecialActionMouseError(
                    "Balatro did not become foreground before special SHOP action"
                )
            if self.focus_poll_interval:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryShopSpecialActionMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
