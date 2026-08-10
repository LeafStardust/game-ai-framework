from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .window import BalatroWindow, BalatroWindowTracker


class BalatroCaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class BalatroFrame:
    sequence: int
    timestamp: float
    window: BalatroWindow
    width: int
    height: int
    bgra: bytes


class ScreenCapturer(Protocol):

    def grab(self, region: dict[str, int]): ...

    def close(self) -> None: ...


class BalatroScreenCapture:
    """Captures only the visible Balatro client area from the desktop."""

    def __init__(
        self,
        tracker: BalatroWindowTracker | None = None,
        capturer: ScreenCapturer | None = None,
    ):
        self.tracker = tracker or BalatroWindowTracker()
        self.capturer = capturer or self._create_capturer()
        self._sequence = 0

    def capture(self) -> BalatroFrame:
        window = self.tracker.snapshot()
        rect = window.client_rect
        region = {
            "left": rect.left,
            "top": rect.top,
            "width": rect.width,
            "height": rect.height,
        }

        try:
            image = self.capturer.grab(region)
            bgra = bytes(image.bgra)
        except Exception as error:
            raise BalatroCaptureError(
                f"unable to capture Balatro client area: {region}"
            ) from error

        expected = rect.width * rect.height * 4
        if len(bgra) != expected:
            raise BalatroCaptureError(
                "captured Balatro frame has unexpected pixel buffer size: "
                f"expected {expected}, got {len(bgra)}"
            )

        self._sequence += 1
        return BalatroFrame(
            sequence=self._sequence,
            timestamp=time.monotonic(),
            window=window,
            width=rect.width,
            height=rect.height,
            bgra=bgra,
        )

    def close(self) -> None:
        close = getattr(self.capturer, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> BalatroScreenCapture:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _create_capturer() -> ScreenCapturer:
        try:
            import mss
        except ImportError as error:
            raise BalatroCaptureError(
                "screen capture requires the 'mss' package; "
                "install requirements.txt"
            ) from error
        return mss.mss()
