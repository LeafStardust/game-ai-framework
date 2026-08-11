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


def _required_geometry(decoder, address: int, *, label: str) -> dict[str, float]:
    fields = decoder.string_fields(int(address))
    geometry = _geometry(decoder, fields.get("T"))
    if not all(name in geometry for name in ("x", "y", "w", "h")):
        raise LiveMemoryHandExecutionError(f"{label} is missing live execution geometry")
    return geometry


class LiveMemoryHandExecutor:
    """Execute hand actions using only live Balatro geometry and normal OS input.

    No screenshot card locator and no calibration file are used. Card targets come
    from the current hand objects' live ``T`` fields; Play Hand / Discard targets
    are resolved from ``G.buttons`` by guarded UI id + callback pairs. The Balatro
    client rectangle and each card's live geometry are refreshed immediately
    before every click, so window changes and hand-selection animations cannot
    invalidate later targets.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver,
        *,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        between_card_delay: float = 0.10,
        selection_timeout: float = 0.80,
        selection_poll_interval: float = 0.02,
        before_action_delay: float = 0.12,
    ) -> None:
        self.observer = observer
        self.mouse = mouse or BalatroMouseController(armed=True)
        self.window_locator = window_locator or BalatroWindowLocator()
        self.between_card_delay = max(0.0, float(between_card_delay))
        self.selection_timeout = max(0.0, float(selection_timeout))
        self.selection_poll_interval = max(0.0, float(selection_poll_interval))
        self.before_action_delay = max(0.0, float(before_action_delay))

    def _current_highlighted_addresses(self) -> set[int]:
        decoder, _, root = self.observer._root()
        hand = _table_fields(decoder, root.get("hand"))
        return {
            address
            for _, address in _array_table_values(decoder, hand.get("highlighted"))
        }

    def _wait_for_highlights(self, expected: set[int]) -> set[int]:
        deadline = time.monotonic() + self.selection_timeout
        while True:
            current = self._current_highlighted_addresses()
            if current == expected:
                return current
            if time.monotonic() >= deadline:
                return current
            if self.selection_poll_interval:
                time.sleep(self.selection_poll_interval)

    def _click_live_card(self, address: int, window, *, label: str):
        decoder, _, root = self.observer._root()
        geometry = _required_geometry(decoder, address, label=label)
        tile_w = _number(root.get("TILE_W"))
        tile_h = _number(root.get("TILE_H"))
        if tile_w is None or tile_h is None:
            raise LiveMemoryHandExecutionError("Balatro TILE_W/TILE_H are unavailable")

        window = self.window_locator.refresh(window.handle)
        transform = BalatroLogicalViewport(
            float(tile_w),
            float(tile_h),
            window.client_rect,
        )
        self.mouse.click_screen(transform.card_center(geometry), window=window)
        return window

    def _rollback_highlights(self, window) -> tuple[bool, set[int]]:
        """Best-effort deselection of every currently highlighted live card."""

        current = self._current_highlighted_addresses()
        if not current:
            return True, set()

        decoder, _, root = self.observer._root()
        hand = _table_fields(decoder, root.get("hand"))
        raw_cards = _array_table_values(decoder, hand.get("cards"))
        hand_order = [address for _, address in raw_cards]

        # Reverse hand order keeps each next target exposed as selected cards drop
        # back into the row and the live geometry is refreshed before every click.
        rollback_order = [address for address in reversed(hand_order) if address in current]
        for address in rollback_order:
            try:
                window = self._click_live_card(address, window, label="highlighted rollback card")
            except Exception:
                return False, self._current_highlighted_addresses()
            expected = set(current)
            expected.discard(address)
            current = self._wait_for_highlights(expected)
            if current != expected:
                return False, current

        final = self._current_highlighted_addresses()
        return not final, final

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
                "one or more live hand cards are already highlighted; deselect them before execution"
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

        # Preserve the original live object addresses as stable identities, but
        # never preserve their initial geometry. Balatro moves/re-fans cards as
        # selections are made, so T must be reread from the object before each click.
        target_addresses = {index: raw_cards[index][1] for index in indices}

        resolve_live_hand_controls(decoder, root)
        window = self.window_locator.find()
        self.mouse.focus(window)

        expected_highlights: set[int] = set()
        try:
            for offset, index in enumerate(indices):
                address = target_addresses[index]

                # Ensure the target object still belongs to the live hand before
                # using its freshly read geometry.
                decoder, _, refreshed_root = self.observer._root()
                refreshed_hand = _table_fields(decoder, refreshed_root.get("hand"))
                current_addresses = {
                    candidate
                    for _, candidate in _array_table_values(decoder, refreshed_hand.get("cards"))
                }
                if address not in current_addresses:
                    raise LiveMemoryHandExecutionError(
                        f"intended card H{index} left the live hand before selection"
                    )

                window = self._click_live_card(address, window, label=f"live card H{index}")
                expected_highlights.add(address)
                actual = self._wait_for_highlights(expected_highlights)
                if actual != expected_highlights:
                    raise LiveMemoryHandExecutionError(
                        f"Balatro highlight mismatch after H{index}: "
                        f"expected={len(expected_highlights)} actual={len(actual)}"
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
                raise LiveMemoryHandExecutionError(
                    "Balatro TILE_W/TILE_H disappeared before action"
                )

            window = self.window_locator.refresh(window.handle)
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            control_point = transform.card_center(control.geometry)
            self.mouse.click_screen(control_point, window=window)
            return indices
        except Exception as error:
            rollback_ok, remaining = self._rollback_highlights(window)
            if rollback_ok:
                raise LiveMemoryHandExecutionError(
                    f"{error}; partial selection rolled back"
                ) from error
            raise LiveMemoryHandExecutionError(
                f"{error}; rollback failed with {len(remaining)} card(s) still highlighted"
            ) from error
