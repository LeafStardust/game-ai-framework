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

# Balatro logical-UI offsets from the selected shop-card center, not pixels.
# The action buttons keep this relative placement across resolution/window changes.
PURCHASE_SPECS = {
    "buy": {
        "child": "buy_button",
        "func": "can_buy",
        "offset": (0.0, 1.55),
    },
    "buy_and_use": {
        "child": "buy_and_use_button",
        "func": "can_buy_and_use",
        "offset": (1.29, 0.0),
    },
}


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
    action: str
    child_name: str
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
    item_click_point: PixelPoint
    screen_point: PixelPoint
    hit_signal: str
    probes: int
    location_source: str
    used_local_search: bool
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


def resolve_live_purchase_target(
    decoder,
    root: dict,
    client_rect: WindowRect,
    *,
    action: str = "buy",
) -> LiveShopBuyTarget:
    spec = PURCHASE_SPECS.get(action)
    if spec is None:
        raise LiveShopPurchaseMouseError(
            f"unsupported shop purchase action: {action!r}"
        )

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    prev_target = _table_fields(decoder, cursor_hover.get("prev_target"))
    children = _table_fields(decoder, prev_target.get("children"))
    child_name = str(spec["child"])
    container_value = children.get(child_name)
    container_address = _table_address(container_value)
    if container_address is None:
        raise LiveShopPurchaseMouseError(
            f"selected shop item has no {child_name} container"
        )

    container = _table_fields(decoder, container_value)
    ui_root_value = container.get("UIRoot")
    ui_root_address = _table_address(ui_root_value)
    if ui_root_address is None:
        raise LiveShopPurchaseMouseError(f"{child_name} has no UIRoot")

    ui_root = _table_fields(decoder, ui_root_value)
    config = _table_fields(decoder, ui_root.get("config"))
    button = _primitive(config.get("button"))
    func = _primitive(config.get("func"))
    control_id = _primitive(config.get("id"))
    expected_func = str(spec["func"])
    if button != EXPECTED_BUTTON or func != expected_func:
        raise LiveShopPurchaseMouseError(
            f"selected shop control is not {action}: "
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
            f"{action} control has no complete UIRoot/container VT/T geometry"
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
        action=action,
        child_name=child_name,
        container_address=container_address,
        ui_root_address=ui_root_address,
        button=str(button),
        func=str(func),
        control_id=control_id,
        geometry_source=geometry_source,
        geometry=dict(geometry),
        screen_center=center,
    )


def resolve_live_buy_target(
    decoder,
    root: dict,
    client_rect: WindowRect,
) -> LiveShopBuyTarget:
    return resolve_live_purchase_target(decoder, root, client_rect, action="buy")


def resolve_live_buy_and_use_target(
    decoder,
    root: dict,
    client_rect: WindowRect,
) -> LiveShopBuyTarget:
    return resolve_live_purchase_target(
        decoder,
        root,
        client_rect,
        action="buy_and_use",
    )


def _active_hover(decoder, fields: dict) -> bool:
    if _primitive(fields.get("hover")) is True:
        return True
    states = _table_fields(decoder, fields.get("states"))
    hover = _table_fields(decoder, states.get("hover"))
    return _primitive(hover.get("is")) is True


def _node_is_purchase(decoder, value, control: LiveShopBuyTarget) -> bool:
    address = _table_address(value)
    seen: set[int] = set()
    expected_addresses = {control.container_address, control.ui_root_address}
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
            _primitive(config.get("button")) == control.button
            and _primitive(config.get("func")) == control.func
        ):
            return True
        address = _table_address(fields.get("parent"))
    return False


def live_purchase_hit_test(
    decoder,
    root: dict,
    control: LiveShopBuyTarget,
) -> tuple[bool, str]:
    for name, address in (
        ("UIRoot", control.ui_root_address),
        ("container", control.container_address),
    ):
        try:
            fields = decoder.string_fields(address)
        except Exception:
            continue
        if _active_hover(decoder, fields):
            return True, f"states.hover.is:{name}"

    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    for name in ("target", "prev_target", "node"):
        if _node_is_purchase(decoder, cursor_hover.get(name), control):
            return True, f"cursor_hover.{name}"
    return False, ""


def live_buy_hit_test(
    decoder,
    root: dict,
    buy: LiveShopBuyTarget,
) -> tuple[bool, str]:
    if buy.action != "buy" or buy.func != "can_buy":
        return False, ""
    return live_purchase_hit_test(decoder, root, buy)


def _template_point(
    item: LiveShopItemTarget,
    *,
    action: str,
    logical_width: float,
    logical_height: float,
    client_rect: WindowRect,
) -> PixelPoint:
    spec = PURCHASE_SPECS[action]
    dx, dy = spec["offset"]
    geometry = item.geometry
    center_x = float(geometry["x"]) + float(geometry["w"]) / 2.0
    center_y = float(geometry["y"]) + float(geometry["h"]) / 2.0
    transform = BalatroLogicalViewport(logical_width, logical_height, client_rect)
    return transform.screen_point(center_x + float(dx), center_y + float(dy))


def _search_offsets(
    x_radius: int,
    y_radius: int,
    step: int,
) -> list[tuple[int, int]]:
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


def _same_item(expected: LiveShopItemTarget, actual: LiveShopItemTarget) -> bool:
    if expected.live_id is not None and actual.live_id is not None:
        return expected.live_id == actual.live_id
    return expected.index == actual.index and expected.label == actual.label


class LiveMemoryShopPurchaseMouseExecutor:
    """Execute Buy or Buy & Use with the real two-click Balatro interaction.

    Sequence:
      1. Click the live shop item itself.
      2. Require the expected generated action child to exist.
      3. Target the action button from a card-relative template.
      4. Require Balatro's exact live hover identity.
      5. Click the action button once.

    Nested control geometry and a bounded local live-hit search remain fail-safe
    fallbacks. No fallback coordinate is persisted.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        action: str = "buy",
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
        if action not in PURCHASE_SPECS:
            raise ValueError(f"unsupported shop purchase action: {action!r}")
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.action = action
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

        selected_item, control = self._click_item_and_resolve_control(
            item,
            window,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
        )
        verified = self._find_verified_purchase_point(
            selected_item,
            window,
            control=control,
            logical_width=float(tile_w),
            logical_height=float(tile_h),
        )

        self.mouse.move_screen(verified.screen_point)
        if self.click_settle_delay > 0:
            time.sleep(self.click_settle_delay)
        decoder, _, root = self.observer._root()
        hit, signal = live_purchase_hit_test(decoder, root, verified.control)
        if not hit:
            raise LiveShopPurchaseMouseError(
                f"verified {self.action} point lost live hover before click"
            )

        self.mouse.click_screen(verified.screen_point, hover_delay=0.0)
        verified = LiveVerifiedShopBuyTarget(
            control=verified.control,
            item_click_point=verified.item_click_point,
            screen_point=verified.screen_point,
            hit_signal=signal,
            probes=verified.probes,
            location_source=verified.location_source,
            used_local_search=verified.used_local_search,
            used_fallback_search=verified.used_fallback_search,
        )
        return before, selected_item, verified

    def _click_item_and_resolve_control(
        self,
        item: LiveShopItemTarget,
        window: BalatroWindow,
        *,
        logical_width: float,
        logical_height: float,
    ) -> tuple[LiveShopItemTarget, LiveShopBuyTarget]:
        # First required click: select/open the shop item itself.
        self.mouse.move_screen(item.screen_center)
        if self.click_settle_delay > 0:
            time.sleep(self.click_settle_delay)
        self.mouse.click_screen(item.screen_center, hover_delay=0.0)
        if self.hover_settle_delay > 0:
            time.sleep(self.hover_settle_delay)

        current = self.observer.observe()
        if current.phase != "SHOP":
            raise LiveShopPurchaseMouseError(
                f"Balatro left SHOP after item selection click: phase={current.phase}"
            )

        selected_item = resolve_live_shop_item_target(
            current,
            index=item.index,
            logical_width=logical_width,
            logical_height=logical_height,
            client_rect=window.client_rect,
        )
        if not _same_item(item, selected_item):
            raise LiveShopPurchaseMouseError(
                "shop item identity changed after selection click"
            )

        decoder, _, root = self.observer._root()
        try:
            control = resolve_live_purchase_target(
                decoder,
                root,
                window.client_rect,
                action=self.action,
            )
        except LiveShopPurchaseMouseError as error:
            child_name = PURCHASE_SPECS[self.action]["child"]
            raise LiveShopPurchaseMouseError(
                f"item selection click did not expose expected {child_name}: {error}"
            ) from error
        return selected_item, control

    def _probe(
        self,
        control: LiveShopBuyTarget,
        point: PixelPoint,
    ) -> tuple[bool, str]:
        self.mouse.move_screen(point)
        if self.probe_settle_delay > 0:
            time.sleep(self.probe_settle_delay)
        decoder, _, root = self.observer._root()
        return live_purchase_hit_test(decoder, root, control)

    def _find_verified_purchase_point(
        self,
        item: LiveShopItemTarget,
        window: BalatroWindow,
        *,
        control: LiveShopBuyTarget,
        logical_width: float,
        logical_height: float,
    ) -> LiveVerifiedShopBuyTarget:
        template = _template_point(
            item,
            action=self.action,
            logical_width=logical_width,
            logical_height=logical_height,
            client_rect=window.client_rect,
        )
        probes = 1
        hit, signal = self._probe(control, template)
        if hit:
            return LiveVerifiedShopBuyTarget(
                control=control,
                item_click_point=item.screen_center,
                screen_point=template,
                hit_signal=signal,
                probes=probes,
                location_source="shop_card_template",
                used_local_search=False,
                used_fallback_search=False,
            )

        # Secondary guess: nested control geometry. It is not authoritative, but it
        # can still be a useful live-derived fallback.
        nested = control.screen_center
        if nested != template:
            probes += 1
            hit, signal = self._probe(control, nested)
            if hit:
                return LiveVerifiedShopBuyTarget(
                    control=control,
                    item_click_point=item.screen_center,
                    screen_point=nested,
                    hit_signal=signal,
                    probes=probes,
                    location_source="nested_geometry",
                    used_local_search=False,
                    used_fallback_search=True,
                )

        # Final fail-safe: bounded local live-hit search around the relative template.
        # Nothing found here is saved or treated as calibration.
        for dx, dy in _search_offsets(
            self.search_x_radius,
            self.search_y_radius,
            self.search_step,
        ):
            point = PixelPoint(template.x + dx, template.y + dy)
            probes += 1
            hit, signal = self._probe(control, point)
            if hit:
                return LiveVerifiedShopBuyTarget(
                    control=control,
                    item_click_point=item.screen_center,
                    screen_point=point,
                    hit_signal=signal,
                    probes=probes,
                    location_source="local_live_search",
                    used_local_search=True,
                    used_fallback_search=True,
                )

        raise LiveShopPurchaseMouseError(
            f"unable to find a live-hit-tested {self.action} point"
        )

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
