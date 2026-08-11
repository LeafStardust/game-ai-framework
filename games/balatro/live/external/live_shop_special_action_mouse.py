from __future__ import annotations

import time
from dataclasses import dataclass

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import LiveMemoryBalatroObserver, _number, _primitive, _table_fields
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindow, BalatroWindowLocator


AREA_PAYLOADS = {
    "vouchers": "shop_vouchers",
    "boosters": "shop_boosters",
}
EXPECTED = {
    "vouchers": (None, "can_redeem"),
    "boosters": ("use_card", "can_open"),
}
MAX_PARENT_DEPTH = 12
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
    """Redeem a voucher or open a booster using live hover authorization only."""

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
        item = _target_item(
            before,
            area,
            index,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
            client_rect=window.client_rect,
        )

        target = None
        for probes, point in enumerate(_search_points(item.screen_center, window.client_rect, self.search_step), start=1):
            self.mouse.move_screen(item.screen_center)
            if self.card_settle_delay:
                time.sleep(self.card_settle_delay)
            self.mouse.move_screen(point)
            if self.probe_settle_delay:
                time.sleep(self.probe_settle_delay)
            hit = live_special_action_hit_test(self.observer, point, area)
            if hit is not None:
                target = LiveShopSpecialActionTarget(
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
            raise LiveShopSpecialActionMouseError(
                f"unable to locate live {area} action control"
            )

        self.mouse.move_screen(item.screen_center)
        if self.card_settle_delay:
            time.sleep(self.card_settle_delay)
        self.mouse.move_screen(target.screen_point)
        if self.click_settle_delay:
            time.sleep(self.click_settle_delay)
        confirmed = live_special_action_hit_test(self.observer, target.screen_point, area)
        if confirmed is None:
            raise LiveShopSpecialActionMouseError(
                f"verified {area} action point lost live hover before click"
            )

        self.mouse.click_screen(target.screen_point, hover_delay=0.0)
        return before, item, target

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
