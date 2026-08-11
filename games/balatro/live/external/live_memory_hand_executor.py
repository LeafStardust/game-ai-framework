from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction

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
from .window import BalatroWindowLocator


class LiveMemoryHandExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveHandControl:
    kind: str
    ui_id: str
    callback: str
    geometry: dict[str, float]
    address: int


@dataclass(frozen=True)
class LiveHandControls:
    play: LiveHandControl
    discard: LiveHandControl


_CONTROL_SPECS = {
    "play": ("play_button", "can_play"),
    "discard": ("discard_button", "can_discard"),
}


def _text(value) -> str | None:
    primitive = _primitive(value)
    return str(primitive) if isinstance(primitive, str) else None


def resolve_live_hand_controls(decoder, root: dict) -> LiveHandControls:
    """Resolve the actual Play Hand and Discard UI elements from ``G.buttons``.

    The resolver requires both the stable UI id and the expected Balatro callback
    plus the element's own ``T`` geometry. It never inherits geometry from an
    ancestor, so hand-area config tables cannot be mistaken for action buttons.
    """

    buttons = _table_fields(decoder, root.get("buttons"))
    ui_root = _table_fields(decoder, buttons.get("UIRoot"))
    children = _array_table_values(decoder, ui_root.get("children"))
    if not children:
        raise LiveMemoryHandExecutionError("G.buttons.UIRoot.children is unavailable")

    found: dict[str, list[LiveHandControl]] = {"play": [], "discard": []}
    for _, address in children:
        fields = decoder.string_fields(address)
        config = _table_fields(decoder, fields.get("config"))
        ui_id = _text(config.get("id"))
        callback = _text(config.get("func"))
        geometry = _geometry(decoder, fields.get("T"))
        if not geometry:
            continue

        for kind, (expected_id, expected_callback) in _CONTROL_SPECS.items():
            if ui_id == expected_id and callback == expected_callback:
                found[kind].append(
                    LiveHandControl(
                        kind=kind,
                        ui_id=ui_id,
                        callback=callback,
                        geometry=geometry,
                        address=address,
                    )
                )

    for kind in ("play", "discard"):
        if len(found[kind]) != 1:
            raise LiveMemoryHandExecutionError(
                f"expected exactly one live {kind} hand control, found {len(found[kind])}"
            )

    return LiveHandControls(play=found["play"][0], discard=found["discard"][0])


def _card_indices(state, action: BalatroAction) -> tuple[int, ...]:
    remaining = list(action.cards)
    indices: list[int] = []

    for index, card in enumerate(state.hand):
        match = next((selected for selected in remaining if selected is card), None)
        if match is None:
            live_id = getattr(card, "live_id", None)
            match = next(
                (
                    selected
                    for selected in remaining
                    if live_id is not None
                    and getattr(selected, "live_id", None) == live_id
                ),
                None,
            )
        if match is not None:
            indices.append(index)
            remaining.remove(match)

    if remaining or len(indices) != len(action.cards):
        raise LiveMemoryHandExecutionError(
            "selected action cards could not be mapped to the current live hand"
        )
    return tuple(indices)


def _stable_id(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


class LiveMemoryHandExecutor:
    """Execute hand actions using only live Balatro geometry and normal OS input.

    No screenshot card locator and no calibration file are used. Card targets come
    from the current hand objects' live ``T`` fields; Play Hand / Discard targets
    are resolved from ``G.buttons`` by guarded UI id + callback pairs. The Balatro
    client rectangle is refreshed immediately before every click so window moves,
    resizes, fullscreen transitions and multi-monitor offsets do not invalidate
    targeting.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver,
        *,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        between_card_delay: float = 0.10,
        selection_settle_delay: float = 0.08,
        before_action_delay: float = 0.12,
    ) -> None:
        self.observer = observer
        self.mouse = mouse or BalatroMouseController(armed=True)
        self.window_locator = window_locator or BalatroWindowLocator()
        self.between_card_delay = max(0.0, float(between_card_delay))
        self.selection_settle_delay = max(0.0, float(selection_settle_delay))
        self.before_action_delay = max(0.0, float(before_action_delay))

    def dispatch(self, action: BalatroAction, state, snapshot) -> tuple[int, ...]:
        if action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            raise LiveMemoryHandExecutionError(
                f"live-memory hand executor cannot dispatch {action.name!r}"
            )
        if not action.cards:
            raise LiveMemoryHandExecutionError("hand action must select at least one card")
        if getattr(state, "phase", None) != "SELECTING_HAND":
            raise LiveMemoryHandExecutionError(
                "live-memory hand execution requires SELECTING_HAND phase"
            )

        decoder, _, root = self.observer._root()
        hand = _table_fields(decoder, root.get("hand"))
        raw_cards = _array_table_values(decoder, hand.get("cards"))
        highlighted = _array_table_values(decoder, hand.get("highlighted"))
        if highlighted:
            raise LiveMemoryHandExecutionError(
                "one or more live hand cards are already highlighted; refusing to toggle selection"
            )

        payload_cards = (snapshot.payload.get("hand") or {}).get("cards") or []
        if len(raw_cards) != len(state.hand) or len(payload_cards) != len(state.hand):
            raise LiveMemoryHandExecutionError(
                "live hand count changed before execution; replan from a fresh checkpoint"
            )

        indices = _card_indices(state, action)
        for index, card in enumerate(state.hand):
            payload_id = _stable_id(payload_cards[index].get("live_id"))
            state_id = _stable_id(getattr(card, "live_id", None))
            if payload_id != state_id:
                raise LiveMemoryHandExecutionError(
                    f"live hand identity mismatch at H{index}: state={state_id!r} snapshot={payload_id!r}"
                )

        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None:
            raise LiveMemoryHandExecutionError("Balatro TILE_W/TILE_H are unavailable")

        controls = resolve_live_hand_controls(decoder, root)
        window = self.window_locator.find()
        self.mouse.focus(window)

        selected_addresses: set[int] = set()
        for offset, index in enumerate(indices):
            geometry = payload_cards[index].get("ui") or {}
            if not all(name in geometry for name in ("x", "y", "w", "h")):
                raise LiveMemoryHandExecutionError(
                    f"live card H{index} is missing execution geometry"
                )

            window = self.window_locator.refresh(window.handle)
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            point = transform.card_center(geometry)
            self.mouse.click_screen(point, window=window)
            if self.selection_settle_delay:
                time.sleep(self.selection_settle_delay)

            # Verify Balatro itself accepted this exact card selection before the
            # executor clicks another card or an action button.
            _, _, refreshed_root = self.observer._root()
            refreshed_hand = _table_fields(decoder, refreshed_root.get("hand"))
            live_highlighted = _array_table_values(decoder, refreshed_hand.get("highlighted"))
            selected_addresses = {address for _, address in live_highlighted}
            expected_address = raw_cards[index][1]
            if expected_address not in selected_addresses:
                raise LiveMemoryHandExecutionError(
                    f"Balatro did not highlight intended card H{index} after click"
                )
            if len(selected_addresses) != offset + 1:
                raise LiveMemoryHandExecutionError(
                    "unexpected live highlighted-card count after selection; refusing to continue"
                )

            if offset + 1 < len(indices) and self.between_card_delay:
                time.sleep(self.between_card_delay)

        if self.before_action_delay:
            time.sleep(self.before_action_delay)

        # Resolve controls again immediately before the final action in case the
        # UIBox was rebuilt while cards were being highlighted.
        decoder, _, root = self.observer._root()
        controls = resolve_live_hand_controls(decoder, root)
        control = controls.play if action.name == PLAY_CARDS else controls.discard
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None:
            raise LiveMemoryHandExecutionError("Balatro TILE_W/TILE_H disappeared before action")

        window = self.window_locator.refresh(window.handle)
        transform = BalatroLogicalViewport(
            float(tile_w),
            float(tile_h),
            window.client_rect,
        )
        control_point = transform.card_center(control.geometry)
        self.mouse.click_screen(control_point, window=window)
        return indices
