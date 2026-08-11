from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .capture import BalatroFrame, BalatroScreenCapture
from .mouse import BalatroMouseController
from .viewport import BalatroViewport, NormalizedPoint


ROUND_EVAL_CONTROLS = {"cash-out"}


class RoundEvalMouseLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoundEvalMouseLayout:
    """Resolution-independent calibrated controls for the ROUND_EVAL screen."""

    cash_out: NormalizedPoint | None = None

    def point_for(self, control: str) -> NormalizedPoint:
        key = str(control).lower().replace("_", "-")
        if key not in ROUND_EVAL_CONTROLS:
            raise RoundEvalMouseLayoutError(
                f"unsupported round-eval control: {control!r}"
            )
        point = self.cash_out
        if point is None:
            raise RoundEvalMouseLayoutError("cash-out control is not calibrated")
        return point

    @classmethod
    def load(cls, path: str | Path) -> "RoundEvalMouseLayout":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RoundEvalMouseLayoutError(
                "round-eval mouse layout must be a JSON object"
            )
        return cls(cash_out=cls._point_from_value(raw.get("cash_out")))

    def to_dict(self) -> dict:
        return {"cash_out": self._point_to_value(self.cash_out)}

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
            raise RoundEvalMouseLayoutError(
                "round-eval mouse target must be an object"
            )
        try:
            return NormalizedPoint(float(value["x"]), float(value["y"]))
        except (KeyError, TypeError, ValueError) as error:
            raise RoundEvalMouseLayoutError(
                f"invalid round-eval mouse target: {value!r}"
            ) from error

    @staticmethod
    def _point_to_value(point: NormalizedPoint | None):
        if point is None:
            return None
        return {"x": point.x, "y": point.y}


class ExternalRoundEvalMouseExecutor:
    """Click one calibrated ROUND_EVAL control through normal desktop input."""

    def __init__(
        self,
        layout: RoundEvalMouseLayout,
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

    def dispatch(self, control: str = "cash-out") -> BalatroFrame:
        point = self.layout.point_for(control)
        frame = self._capture_focused_frame()
        self.mouse.click_screen(BalatroViewport(frame).screen_point(point))
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
                raise RoundEvalMouseLayoutError(
                    "Balatro did not become foreground before round-eval capture"
                )
            if self.focus_poll_interval > 0:
                time.sleep(self.focus_poll_interval)

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> "ExternalRoundEvalMouseExecutor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
