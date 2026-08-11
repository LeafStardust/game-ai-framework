from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Callable

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.state import BalatroState

from .capture import BalatroFrame, BalatroScreenCapture
from .card_capture import DEFAULT_HAND_REGION
from .card_locator import CardFaceLocation, locate_card_faces
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint, PixelPoint


HAND_CONTROLS = {"play-hand", "discard"}


class HandMouseLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class HandMouseLayout:
    """Resolution-independent fixed action buttons for a dealt Balatro hand."""

    play_hand: NormalizedPoint | None = None
    discard: NormalizedPoint | None = None

    def point_for(self, control: str) -> NormalizedPoint:
        key = str(control).lower()
        if key == "play-hand":
            point = self.play_hand
        elif key == "discard":
            point = self.discard
        else:
            raise HandMouseLayoutError(f"unsupported hand control: {control!r}")
        if point is None:
            raise HandMouseLayoutError(f"{key} button is not calibrated")
        return point

    @classmethod
    def load(cls, path: str | Path) -> "HandMouseLayout":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise HandMouseLayoutError("hand mouse layout must be a JSON object")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "HandMouseLayout":
        return cls(
            play_hand=cls._point_from_value(raw.get("play_hand")),
            discard=cls._point_from_value(raw.get("discard")),
        )

    def to_dict(self) -> dict:
        return {
            "play_hand": self._point_to_value(self.play_hand),
            "discard": self._point_to_value(self.discard),
        }

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    @staticmethod
    def _point_from_value(value) -> NormalizedPoint | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise HandMouseLayoutError("hand mouse target must be an object")
        try:
            return NormalizedPoint(float(value["x"]), float(value["y"]))
        except (KeyError, TypeError, ValueError) as error:
            raise HandMouseLayoutError(
                f"invalid hand mouse target: {value!r}"
            ) from error

    @staticmethod
    def _point_to_value(point: NormalizedPoint | None):
        if point is None:
            return None
        return {"x": point.x, "y": point.y}


class ExternalHandMouseExecutor:
    """Execute one PLAY_CARDS or DISCARD_CARDS action through normal mouse input."""

    def __init__(
        self,
        layout: HandMouseLayout,
        capture: BalatroScreenCapture | None = None,
        mouse: BalatroMouseController | None = None,
        *,
        card_locator: Callable[..., list[CardFaceLocation]] = locate_card_faces,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
        between_card_delay: float = 0.12,
        before_action_delay: float = 0.20,
        pre_capture_point: NormalizedPoint | None = None,
        pre_capture_settle_delay: float = 0.20,
    ):
        self.layout = layout
        self.capture = capture or BalatroScreenCapture()
        self.mouse = mouse or BalatroMouseController()
        self.card_locator = card_locator
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)
        self.between_card_delay = max(0.0, between_card_delay)
        self.before_action_delay = max(0.0, before_action_delay)
        self.pre_capture_point = pre_capture_point
        self.pre_capture_settle_delay = max(0.0, pre_capture_settle_delay)

    def locate_hand(
        self,
        state: BalatroState,
    ) -> tuple[BalatroFrame, list[CardFaceLocation]]:
        frame = self._capture_focused_frame()
        region = BalatroViewport(frame).crop(DEFAULT_HAND_REGION)
        locations = self.card_locator(region)
        if len(locations) != len(state.hand):
            raise HandMouseLayoutError(
                "visible hand/card-save count mismatch: "
                f"screen={len(locations)}, save={len(state.hand)}. "
                "Make sure no hand cards are already selected."
            )
        self._require_unselected_row(locations)
        return frame, locations

    def dispatch(
        self,
        action: BalatroAction,
        state: BalatroState,
    ) -> tuple[int, ...]:
        self._validate_action(action)
        frame, locations = self.locate_hand(state)
        return self.dispatch_with_locations(action, state, frame, locations)

    def dispatch_with_locations(
        self,
        action: BalatroAction,
        state: BalatroState,
        frame: BalatroFrame,
        locations: list[CardFaceLocation],
    ) -> tuple[int, ...]:
        """Dispatch against one already validated frozen hand mapping."""

        self._validate_action(action)
        if len(locations) != len(state.hand):
            raise HandMouseLayoutError(
                "frozen hand/card-save count mismatch: "
                f"screen={len(locations)}, save={len(state.hand)}"
            )
        self._require_unselected_row(locations)

        indices = self.card_indices(state, action)
        viewport = BalatroViewport(frame)

        for offset, index in enumerate(indices):
            self.mouse.click_screen(viewport.screen_point(locations[index].center))
            if offset + 1 < len(indices) and self.between_card_delay > 0:
                time.sleep(self.between_card_delay)

        if self.before_action_delay > 0:
            time.sleep(self.before_action_delay)

        control = "play-hand" if action.name == PLAY_CARDS else "discard"
        self.mouse.click_screen(viewport.screen_point(self.layout.point_for(control)))
        return indices

    @staticmethod
    def _validate_action(action: BalatroAction) -> None:
        if action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            raise HandMouseLayoutError(
                f"external hand executor cannot dispatch {action.name!r}"
            )
        if not action.cards:
            raise HandMouseLayoutError("hand action must select at least one card")

    @staticmethod
    def card_indices(
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[int, ...]:
        remaining = list(action.cards)
        indices: list[int] = []

        for index, card in enumerate(state.hand):
            match = next(
                (selected for selected in remaining if selected is card),
                None,
            )
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
            raise HandMouseLayoutError(
                "selected action cards could not be mapped to current save hand"
            )
        return tuple(indices)

    @staticmethod
    def _require_unselected_row(locations: list[CardFaceLocation]) -> None:
        if len(locations) < 2:
            return

        centers = [location.center.y for location in locations]
        heights = [location.normalized_rect.height for location in locations]
        tolerance = max(0.008, median(heights) * 0.20)
        if max(centers) - min(centers) > tolerance:
            raise HandMouseLayoutError(
                "visible hand is not on one resting row; one or more cards may "
                "already be selected. Deselect all hand cards before external execution."
            )

    def _capture_focused_frame(self) -> BalatroFrame:
        tracker = getattr(self.capture, "tracker", None)
        if tracker is not None:
            window = tracker.snapshot()
            self.mouse.focus(window)
            self._wait_for_foreground(tracker, window.handle)
            self._clear_hover(window)
            if self.focus_settle_delay > 0:
                time.sleep(self.focus_settle_delay)
            return self.capture.capture()

        frame = self.capture.capture()
        self.mouse.focus(frame.window)
        self._clear_hover(frame.window)
        if self.focus_settle_delay > 0:
            time.sleep(self.focus_settle_delay)
        if self.pre_capture_point is not None:
            return self.capture.capture()
        return frame

    def _clear_hover(self, window) -> None:
        if self.pre_capture_point is None:
            return
        rect = window.client_rect
        point = PixelPoint(
            rect.left + round(rect.width * self.pre_capture_point.x),
            rect.top + round(rect.height * self.pre_capture_point.y),
        )
        self.mouse.move_screen(point)
        if self.pre_capture_settle_delay > 0:
            time.sleep(self.pre_capture_settle_delay)

    def _wait_for_foreground(self, tracker, handle: int) -> None:
        locator = getattr(tracker, "locator", None)
        foreground_handle = getattr(locator, "foreground_handle", None)
        if not callable(foreground_handle):
            return

        deadline = time.monotonic() + self.focus_timeout
        while True:
            if foreground_handle() == handle:
                return
            if time.monotonic() >= deadline:
                raise HandMouseLayoutError(
                    "Balatro did not become foreground before hand capture"
                )
            if self.focus_poll_interval > 0:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalHandMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
