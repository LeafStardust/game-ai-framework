from __future__ import annotations

import time
from dataclasses import dataclass

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_pack_selected_card_confirm_mouse import (
    LivePackConfirmTarget,
    LivePackSelectedCardConfirmExecutor,
    pack_contains_card,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator


class LivePackCardMouseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LivePackCardTarget:
    index: int
    address: int
    screen_center: PixelPoint


@dataclass(frozen=True)
class LivePackCardDispatchResult:
    phase_before: str
    phase_after: str
    card: LivePackCardTarget
    selection_point: PixelPoint
    confirm: LivePackConfirmTarget
    selected_card_consumed: bool


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _pack_card_addresses(observer: LiveMemoryBalatroObserver) -> list[int]:
    decoder, _, root = observer._root()
    area = _table_fields(decoder, root.get("pack_cards"))
    return [address for _, address in _array_table_values(decoder, area.get("cards"))]


def _highlighted_addresses(observer: LiveMemoryBalatroObserver) -> list[int]:
    decoder, _, root = observer._root()
    area = _table_fields(decoder, root.get("pack_cards"))
    return [address for _, address in _array_table_values(decoder, area.get("highlighted"))]


def _card_click_can(observer: LiveMemoryBalatroObserver, address: int) -> bool:
    decoder, _, _ = observer._root()
    fields = decoder.string_fields(address)
    states = _table_fields(decoder, fields.get("states"))
    click = _table_fields(decoder, states.get("click"))
    return _primitive(click.get("can")) is True


def _card_geometry(observer: LiveMemoryBalatroObserver, address: int) -> dict[str, float]:
    decoder, _, _ = observer._root()
    fields = decoder.string_fields(address)
    for value in (fields.get("VT"), fields.get("T")):
        geometry = _geometry(decoder, value)
        if all(name in geometry for name in ("x", "y", "w", "h")):
            return geometry
    raise LivePackCardMouseError("pack card has no complete VT/T geometry")


def _cursor_target_address(observer: LiveMemoryBalatroObserver) -> int | None:
    decoder, _, root = observer._root()
    controller = _table_fields(decoder, root.get("CONTROLLER"))
    cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
    return _table_address(cursor_hover.get("target"))


class LivePackCardMouseExecutor:
    """Select and take one visible booster-pack card using two normal mouse clicks.

    The first click is authorized only when Balatro's live cursor target is the
    requested ``G.pack_cards`` card. The second click is delegated to the already
    validated ``use_card/can_select_card`` confirm executor.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        *,
        selection_settle_delay: float = 0.12,
        highlight_timeout: float = 2.0,
        result_timeout: float = 8.0,
        poll_interval: float = 0.05,
        focus_settle_delay: float = 0.25,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.selection_settle_delay = max(0.0, selection_settle_delay)
        self.highlight_timeout = max(0.0, highlight_timeout)
        self.result_timeout = max(0.0, result_timeout)
        self.poll_interval = max(0.0, poll_interval)
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self._owns_observer = observer is None

    def _resolve_target(self, index: int, window) -> LivePackCardTarget:
        snapshot = self.observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            raise LivePackCardMouseError(
                f"Balatro is in {snapshot.phase}, expected *_PACK"
            )
        cards = _pack_card_addresses(self.observer)
        if index < 0 or index >= len(cards):
            raise LivePackCardMouseError(
                f"pack card index {index} out of range for {len(cards)} visible cards"
            )
        address = cards[index]
        if not _card_click_can(self.observer, address):
            raise LivePackCardMouseError("target pack card is not live-clickable")

        decoder, _, root = self.observer._root()
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
            raise LivePackCardMouseError("missing positive G.TILE_W / G.TILE_H")
        geometry = _card_geometry(self.observer, address)
        transform = BalatroLogicalViewport(float(tile_w), float(tile_h), window.client_rect)
        return LivePackCardTarget(
            index=index,
            address=address,
            screen_center=transform.card_center(geometry),
        )

    def dispatch(self, index: int) -> LivePackCardDispatchResult:
        window = self.window_locator.find()
        self.mouse.focus(window)
        if self.focus_settle_delay:
            time.sleep(self.focus_settle_delay)
        window = self.window_locator.refresh(window.handle)

        before = self.observer.observe()
        if not before.phase.endswith("_PACK"):
            raise LivePackCardMouseError(
                f"Balatro is in {before.phase}, expected *_PACK"
            )
        target = self._resolve_target(index, window)

        # Freshly resolve immediately before the irreversible selection click.
        fresh = self._resolve_target(index, window)
        if fresh.address != target.address:
            raise LivePackCardMouseError("pack card identity changed before selection click")
        target = fresh

        self.mouse.move_screen(target.screen_center)
        if self.selection_settle_delay:
            time.sleep(self.selection_settle_delay)
        if _cursor_target_address(self.observer) != target.address:
            raise LivePackCardMouseError(
                "live cursor target does not match requested pack card before click"
            )
        if not _card_click_can(self.observer, target.address):
            raise LivePackCardMouseError("pack card lost click eligibility before click")
        self.mouse.click_screen(target.screen_center, hover_delay=0.0)

        deadline = time.monotonic() + self.highlight_timeout
        while True:
            highlighted = _highlighted_addresses(self.observer)
            if highlighted == [target.address]:
                break
            if time.monotonic() >= deadline:
                raise LivePackCardMouseError(
                    "pack card selection click did not produce exactly one matching highlight"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)

        confirm_executor = LivePackSelectedCardConfirmExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        _, selected, confirm = confirm_executor.dispatch()
        if selected.address != target.address:
            raise LivePackCardMouseError("highlighted card changed before confirm click")

        deadline = time.monotonic() + self.result_timeout
        phase_after = before.phase
        consumed = False
        while True:
            after = self.observer.observe()
            phase_after = after.phase
            consumed = not pack_contains_card(self.observer, target.address)
            if consumed or phase_after != before.phase:
                break
            if time.monotonic() >= deadline:
                raise LivePackCardMouseError(
                    "timed out verifying selected pack card was consumed"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)

        return LivePackCardDispatchResult(
            phase_before=before.phase,
            phase_after=phase_after,
            card=target,
            selection_point=target.screen_center,
            confirm=confirm,
            selected_card_consumed=consumed,
        )

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LivePackCardMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
