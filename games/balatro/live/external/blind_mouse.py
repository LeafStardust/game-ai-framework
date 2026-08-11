from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .capture import BalatroFrame, BalatroScreenCapture
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint


BLIND_TARGETS = {"small", "big", "boss"}
BLIND_CONTROLS = {
    "small-select",
    "small-skip",
    "big-select",
    "big-skip",
    "boss-select",
}


class BlindMouseLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlindMouseLayout:
    """Resolution-independent calibrated blind Select/Skip control points."""

    small_select: NormalizedPoint | None = None
    small_skip: NormalizedPoint | None = None
    big_select: NormalizedPoint | None = None
    big_skip: NormalizedPoint | None = None
    boss_select: NormalizedPoint | None = None

    def point_for(self, control: str) -> NormalizedPoint:
        key = str(control).lower().replace("_", "-")
        if key not in BLIND_CONTROLS:
            raise BlindMouseLayoutError(f"unsupported blind control: {control!r}")
        point = getattr(self, key.replace("-", "_"))
        if point is None:
            raise BlindMouseLayoutError(f"{key} control is not calibrated")
        return point

    @classmethod
    def load(cls, path: str | Path) -> "BlindMouseLayout":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise BlindMouseLayoutError("blind mouse layout must be a JSON object")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "BlindMouseLayout":
        # Accept the first experimental flat select-only format so local calibration
        # files do not become unreadable if one was already created.
        return cls(
            small_select=cls._point_from_value(
                raw.get("small_select", raw.get("small"))
            ),
            small_skip=cls._point_from_value(raw.get("small_skip")),
            big_select=cls._point_from_value(raw.get("big_select", raw.get("big"))),
            big_skip=cls._point_from_value(raw.get("big_skip")),
            boss_select=cls._point_from_value(
                raw.get("boss_select", raw.get("boss"))
            ),
        )

    def to_dict(self) -> dict:
        return {
            "small_select": self._point_to_value(self.small_select),
            "small_skip": self._point_to_value(self.small_skip),
            "big_select": self._point_to_value(self.big_select),
            "big_skip": self._point_to_value(self.big_skip),
            "boss_select": self._point_to_value(self.boss_select),
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
            raise BlindMouseLayoutError("blind mouse target must be an object")
        try:
            return NormalizedPoint(float(value["x"]), float(value["y"]))
        except (KeyError, TypeError, ValueError) as error:
            raise BlindMouseLayoutError(
                f"invalid blind mouse target: {value!r}"
            ) from error

    @staticmethod
    def _point_to_value(point: NormalizedPoint | None):
        if point is None:
            return None
        return {"x": point.x, "y": point.y}


class ExternalBlindMouseExecutor:
    """Click one calibrated blind Select/Skip control through desktop input."""

    def __init__(
        self,
        layout: BlindMouseLayout,
        capture: BalatroScreenCapture | None = None,
        mouse: BalatroMouseController | None = None,
        *,
        focus_settle_delay: float = 0.25,
        focus_timeout: float = 1.5,
        focus_poll_interval: float = 0.02,
    ):
        self.layout = layout
        self.capture = capture or BalatroScreenCapture()
        self.mouse = mouse or BalatroMouseController()
        self.focus_settle_delay = max(0.0, focus_settle_delay)
        self.focus_timeout = max(0.0, focus_timeout)
        self.focus_poll_interval = max(0.0, focus_poll_interval)

    def dispatch(self, control: str) -> BalatroFrame:
        point = self.layout.point_for(control)
        frame = self._capture_focused_frame()
        viewport = BalatroViewport(frame)
        self.mouse.click_screen(viewport.screen_point(point))
        return frame

    def _capture_focused_frame(self) -> BalatroFrame:
        tracker = getattr(self.capture, "tracker", None)
        if tracker is not None:
            window = tracker.snapshot()
            self.mouse.focus(window)
            self._wait_for_foreground(tracker, window.handle)
            if self.focus_settle_delay > 0:
                time.sleep(self.focus_settle_delay)
            return self.capture.capture()

        frame = self.capture.capture()
        self.mouse.focus(frame.window)
        if self.focus_settle_delay > 0:
            time.sleep(self.focus_settle_delay)
        return frame

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
                raise BlindMouseLayoutError(
                    "Balatro focus was requested, but Windows did not report Balatro as "
                    "the foreground window before blind control capture"
                )
            if self.focus_poll_interval > 0:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalBlindMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
