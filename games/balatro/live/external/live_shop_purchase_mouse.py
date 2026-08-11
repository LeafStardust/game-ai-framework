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


REQUIRED_GEOMETRY = ("x", "y", "w", "h")
EXPECTED_BUTTON = "buy_from_shop"
EXPECTED_FUNC = "can_buy"


class LiveShopPurchaseMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveShopItemTarget:
    area: str
    index: int
    label: str | None
    live_id: object
    ability_set: str | None
    cost: float
    geometry: dict[str, float]
    screen_center: PixelPoint


@dataclass(frozen=True)
class LiveShopBuyTarget:
    container_address: int
    ui_root_address: int
    button: str
    func: str
    control_id: object
    geometry_source: str
    geometry: dict[str, float]
    screen_center: PixelPoint


@dataclass(frozen=True)
class LiveVerifiedShopBuyTarget:
    control: LiveShopBuyTarget
    screen_point: PixelPoint
    hit_signal: str
    probes: int
    used_fallback_search: bool


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _complete_geometry(value: dict[str, float]) -> bool:
    return all(name in value for name in REQUIRED_GEOMETRY)


def _main_cards(snapshot: LiveBalatroSnapshot) -> list[dict]:
    return list((snapshot.payload.get("shop_jokers") or {}).get("cards") or [])


def resolve_live_shop_item_target(
    snapshot: LiveBalatroSnapshot,
    *,
    index: int,
    logical_width: float,
    logical_height: float,
    client_rect: WindowRect,
) -> LiveShopItemTarget:
    if snapshot.phase != "SHOP":
        raise LiveShopPurchaseMouseError(
            f"Balatro is in {snapshot.phase}, expected SHOP"
        )
    if index < 0:
        raise LiveShopPurchaseMouseError("shop item index cannot be negative")

    cards = _main_cards(snapshot)
    matches = [
        card
        for position, card in enumerate(cards)
        if int(card.get("area_index", position)) == index
    ]
    if len(matches) != 1:
        raise LiveShopPurchaseMouseError(
            f"expected exactly one visible main-shop item at index {index}, "
            f"found {len(matches)}"
        )

    card = matches[0]
    geometry = dict(card.get("ui") or {})
    if not _complete_geometry(geometry):
        raise LiveShopPurchaseMouseError(
            "target shop item has no complete live geometry"
        )

    cost_value = card.get("cost")
    if not isinstance(cost_value, (int, float)):
        raise LiveShopPurchaseMouseError("target shop item has no numeric live cost")
    cost = float(cost_value)
    money = snapshot.payload.get("money")
    if isinstance(money, (int, float)) and float(money) < cost:
        raise LiveShopPurchaseMouseError(
            f"target shop item is unaffordable: money={money}, cost={cost}"
        )

    transform = BalatroLogicalViewport(
        float(logical_width),
        float(logical_height),
        client_rect,
    )
    center = transform.card_center(geometry)
    return LiveShopItemTarget(
        area="main",
        index=index,
        label=card.get("label") or card.get("ability_name") or card.get("center"),
        live_id=card.get("live_id"),
        ability_set=card.get("ability_set"),
        cost=cost,
        geometry=geometry,
        screen_center=center,
    )


def resolve_live_buy_target(
    decoder,
    root: dict,
    client_rect: WindowRect,
) -> LiveShopBuyTarget:
    """Resolve the ordinary Buy control created for the hovered shop item.

    ``screen_center`` is only a geometry-derived first guess. Nested Balatro UI
    transforms are not assumed to be globally positioned; callers must live
    hit-test the point before clicking it.
    """

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    prev_target = _table_fields(decoder, cursor_hover.get("prev_target"))
    children = _table_fields(decoder, prev_target.get("children"))
    buy_container_value = children.get("buy_button")
    container_address = _table_address(buy_container_value)
    if container_address is None:
        raise LiveShopPurchaseMouseError(
            "hovered shop item has no buy_button container"
        )

    container = _table_fields(decoder, buy_container_value)
    ui_root_value = container.get("UIRoot")
    ui_root_address = _table_address(ui_root_value)
    if ui_root_address is None:
        raise LiveShopPurchaseMouseError("buy_button has no UIRoot")

    ui_root = _table_fields(decoder, ui_root_value)
    config = _table_fields(decoder, ui_root.get("config"))
    button = _primitive(config.get("button"))
    func = _primitive(config.get("func"))
    control_id = _primitive(config.get("id"))
    if button != EXPECTED_BUTTON or func != EXPECTED_FUNC:
        raise LiveShopPurchaseMouseError(
            "hover purchase control is not the ordinary Buy control: "
            f"button={button!r}, func={func!r}, id={control_id!r}"
        )

    sources = (
        ("UIRoot VT", _geometry(decoder, ui_root.get("VT"))),
        ("UIRoot T", _geometry(decoder, ui_root.get("T"))),
        ("Container VT", _geometry(decoder, container.get("VT"))),
        ("Container T", _geometry(decoder, container.get("T"))),
    )
    geometry_source = ""
    geometry: dict[str, float] = {}
    for name, candidate in sources:
        if _complete_geometry(candidate):
            geometry_source = name
            geometry = candidate
            break
    if not geometry:
        raise LiveShopPurchaseMouseError(
            "ordinary Buy control has no complete UIRoot/container VT/T geometry"
        )

    tile_w = _number(root.get("TILE_W"))
    tile_h = _number(root.get("TILE_H"))
    if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
        raise LiveShopPurchaseMouseError("missing positive G.TILE_W / G.TILE_H")

    transform = BalatroLogicalViewport(float(tile_w), float(tile_h), client_rect)
    center = transform.screen_point(
        float(geometry["x"]) + float(geometry["w"]) / 2.0,
        float(geometry["y"]) + float(geometry["h"]) / 2.0,
    )
    return LiveShopBuyTarget(
        container_address=container_address,
        ui_root_address=ui_root_address,
        button=str(button),
        func=str(func),
        control_id=control_id,
        geometry_source=geometry_source,
        geometry=dict(geometry),
        screen_center=center,
    )


def _active_hover(decoder, fields: dict) -> bool:
    if _primitive(fields.get("hover")) is True:
        return True
    states = _table_fields(decoder, fields.get("states"))
    hover = _table_fields(decoder, states.get("hover"))
    return _primitive(hover.get("is")) is True


def _node_is_buy(decoder, value, *, expected_addresses: set[int]) -> bool:
    address = _table_address(value)
    seen: set[int] = set()
    for _ in range(12):
        if address is None or address in seen:
            return False
        if address in expected_addresses:
            return True
        seen.add(address)
        try:
            fields = decoder.string_fields(address)
        except Exception:
            return False
        config = _table_fields(decoder, fields.get("config"))
        if (
            _primitive(config.get("button")) == EXPECTED_BUTTON
            and _primitive(config.get("func")) == EXPECTED_FUNC
        ):
            return True
        address = _table_address(fields.get("parent"))
    return False


def live_buy_hit_test(decoder, root: dict, buy: LiveShopBuyTarget) -> tuple[bool, str]:
    """Ask Balatro whether the current cursor is actually over this Buy control."""

    for name, address in (
        ("UIRoot", buy.ui_root_address),
        ("container", buy.container_address),
    ):
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue
        if _active_hover(decoder, fields):
            return True, f"states.hover.is:{name}"

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    expected_addresses = {buy.container_address, buy.ui_root_address}
    for name in ("target", "prev_target", "node"):
        if _node_is_buy(
            decoder,
            cursor_hover.get(name),
            expected_addresses=expected_addresses,
        ):
            return True, f"cursor_hover.{name}"
    return False, ""


def _search_offsets(x_radius: int, y_radius: int, step: int) -> list[tuple[int, int]]:
    offsets = [
        (dx, dy)
        for dx in range(-x_radius, x_radius + 1, step)
        for dy in range(-y_radius, y_radius + 1, step)
        if dx != 0 or dy != 0
    ]
    offsets.sort(
        key=lambda value: (
            abs(value[0]) + abs(value[1]),
            abs(value[1]),
            abs(value[0]),
        )
    )
    return offsets


class LiveMemoryShopPurchaseMouseExecutor:
    """Buy one main-shop item using live memory plus normal desktop mouse input.

    The nested Buy geometry is treated only as a first guess. No Buy click is
    sent until Balatro's own live hover state confirms the cursor is currently
    inside the ordinary ``buy_from_shop / can_buy`` control.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        hover_settle_delay: float = 0.15,
        probe_settle_delay: float = 0.10,
        click_settle_delay: float = 0.05,
        search_x_radius: int = 160,
        search_y_radius: int = 180,
        search_step: int = 20,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.hover_settle_delay = max(0.0, hover_settle_delay)
        self.probe_settle_delay = max(0.0, probe_settle_delay)
        self.click_settle_delay = max(0.0, click_settle_delay)
        self.search_x_radius = max(1, int(search_x_radius))
        self.search_y_radius = max(1, int(search_y_radius))
        self.search_step = max(1, int(search_step))
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)
        self._owns_observer = observer is None

    def preview(
        self,
        index: int,
    ) -> tuple[LiveBalatroSnapshot, LiveShopItemTarget, BalatroWindow]:
        window = self.window_locator.find()
        snapshot = self.observer.observe()
        decoder, _, root = self.observer._root()
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
            raise LiveShopPurchaseMouseError("missing positive G.TILE_W / G.TILE_H")
        target = resolve_live_shop_item_target(
            snapshot,
            index=index,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
            client_rect=window.client_rect,
        )
        return snapshot, target, window

    def dispatch(
        self,
        index: int,
    ) -> tuple[LiveBalatroSnapshot, LiveShopItemTarget, LiveVerifiedShopBuyTarget]:
        window = self.window_locator.find()
        self.mouse.focus(window)
        self._wait_for_foreground(window.handle)
        if self.focus_settle_delay > 0:
            time.sleep(self.focus_settle_delay)

        window = self.window_locator.refresh(window.handle)
        before = self.observer.observe()
        decoder, _, root = self.observer._root()
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
            raise LiveShopPurchaseMouseError("missing positive G.TILE_W / G.TILE_H")

        item = resolve_live_shop_item_target(
            before,
            index=index,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
            client_rect=window.client_rect,
        )
        verified = self._find_verified_buy_point(item, window)

        # Keep the cursor on the already verified point, then re-check the same
        # live Buy object immediately before the click. Fail closed if Balatro no
        # longer considers the pointer to be inside that control.
        self.mouse.move_screen(verified.screen_point)
        if self.click_settle_delay > 0:
            time.sleep(self.click_settle_delay)
        decoder, _, root = self.observer._root()
        hit, signal = live_buy_hit_test(decoder, root, verified.control)
        if not hit:
            raise LiveShopPurchaseMouseError(
                "verified Buy point lost live hover before click"
            )

        self.mouse.click_screen(verified.screen_point, hover_delay=0.0)
        verified = LiveVerifiedShopBuyTarget(
            control=verified.control,
            screen_point=verified.screen_point,
            hit_signal=signal,
            probes=verified.probes,
            used_fallback_search=verified.used_fallback_search,
        )
        return before, item, verified

    def _find_verified_buy_point(
        self,
        item: LiveShopItemTarget,
        window: BalatroWindow,
    ) -> LiveVerifiedShopBuyTarget:
        initial_buy = self._resolve_buy_after_hover(item, window)
        origin = initial_buy.screen_center
        candidates = [origin] + [
            PixelPoint(origin.x + dx, origin.y + dy)
            for dx, dy in _search_offsets(
                self.search_x_radius,
                self.search_y_radius,
                self.search_step,
            )
        ]

        for probe_count, point in enumerate(candidates, start=1):
            buy = self._resolve_buy_after_hover(item, window)
            self.mouse.move_screen(point)
            if self.probe_settle_delay > 0:
                time.sleep(self.probe_settle_delay)
            decoder, _, root = self.observer._root()
            hit, signal = live_buy_hit_test(decoder, root, buy)
            if hit:
                return LiveVerifiedShopBuyTarget(
                    control=buy,
                    screen_point=point,
                    hit_signal=signal,
                    probes=probe_count,
                    used_fallback_search=probe_count > 1,
                )

        raise LiveShopPurchaseMouseError(
            "unable to find a live-hit-tested ordinary Buy point around nested geometry"
        )

    def _resolve_buy_after_hover(
        self,
        item: LiveShopItemTarget,
        window: BalatroWindow,
    ) -> LiveShopBuyTarget:
        self.mouse.move_screen(item.screen_center)
        if self.hover_settle_delay > 0:
            time.sleep(self.hover_settle_delay)

        current = self.observer.observe()
        if current.phase != "SHOP":
            raise LiveShopPurchaseMouseError(
                f"Balatro left SHOP before Buy click: phase={current.phase}"
            )
        decoder, _, root = self.observer._root()
        return resolve_live_buy_target(decoder, root, window.client_rect)

    def _wait_for_foreground(self, handle: int) -> None:
        foreground_handle = getattr(self.window_locator, "foreground_handle", None)
        if not callable(foreground_handle):
            return

        deadline = time.monotonic() + self.focus_timeout
        while True:
            if foreground_handle() == handle:
                return
            if time.monotonic() >= deadline:
                raise LiveShopPurchaseMouseError(
                    "Balatro did not become foreground before shop purchase"
                )
            if self.focus_poll_interval > 0:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryShopPurchaseMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
