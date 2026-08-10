from __future__ import annotations

import struct
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
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
        window = self.tracker.require_foreground()
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


def save_frame_png(frame: BalatroFrame, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = bytearray()
    stride = frame.width * 4
    for y in range(frame.height):
        rows.append(0)
        row = frame.bgra[y * stride : (y + 1) * stride]
        for index in range(0, len(row), 4):
            blue, green, red = row[index : index + 3]
            rows.extend((red, green, blue))

    header = struct.pack(
        ">IIBBBBB",
        frame.width,
        frame.height,
        8,
        2,
        0,
        0,
        0,
    )
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", header))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(rows))))
    png.extend(_png_chunk(b"IEND", b""))
    output.write_bytes(png)
    return output


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", checksum)
    )
