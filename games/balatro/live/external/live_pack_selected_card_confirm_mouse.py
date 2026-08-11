from __future__ import annotations

import time
from dataclasses import dataclass

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _primitive,
    _table_fields,
)
from .mouse import BalatroMouseController
from .viewport import PixelPoint
from .window import BalatroWindowLocator

EXPECTED_BUTTON = "use_card"
EXPECTED_FUNC = "can_select_card"
MAX_PARENT_DEPTH = 12


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


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


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
            )
    return None


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
        probe_settle_delay: float = 0.06,
        click_settle_delay: float = 0.05,
        focus_settle_delay: float = 0.25,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController()
        self.window_locator = window_locator or BalatroWindowLocator()
        self.search_step = max(1, int(search_step))
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

        target = None
        for probes, point in enumerate(
            _search_points(window.client_rect, self.search_step), start=1
        ):
            self.mouse.move_screen(point)
            if self.probe_settle_delay:
                time.sleep(self.probe_settle_delay)
            hit = live_confirm_hit_test(self.observer, point)
            if hit is not None:
                target = LivePackConfirmTarget(
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
            raise LivePackSelectedCardConfirmError(
                "unable to locate live use_card/can_select_card control"
            )

        self.mouse.move_screen(target.screen_point)
        if self.click_settle_delay:
            time.sleep(self.click_settle_delay)
        confirmed = live_confirm_hit_test(self.observer, target.screen_point)
        if confirmed is None:
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
