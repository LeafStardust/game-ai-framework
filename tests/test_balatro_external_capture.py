import struct

import pytest

from games.balatro.live.external import (
    BalatroCaptureError,
    BalatroScreenCapture,
    BalatroWindow,
    WindowRect,
)
from games.balatro.live.external.capture import save_frame_png


class Tracker:

    def __init__(self, windows):
        self.windows = iter(windows)

    def snapshot(self):
        return next(self.windows)


class Image:

    def __init__(self, bgra):
        self.bgra = bgra


class Capturer:

    def __init__(self, fill=b"\x00\x00\x00\xff"):
        self.fill = fill
        self.regions = []
        self.closed = False

    def grab(self, region):
        self.regions.append(region)
        pixels = region["width"] * region["height"]
        return Image(self.fill * pixels)

    def close(self):
        self.closed = True


def window(left=10, top=20, width=4, height=3):
    return BalatroWindow(
        handle=1,
        title="Balatro",
        client_rect=WindowRect(left, top, width, height),
    )


def test_capture_uses_current_balatro_client_area():
    first = window()
    second = window(left=100, top=200, width=5, height=2)
    capturer = Capturer()
    capture = BalatroScreenCapture(
        tracker=Tracker([first, second]),
        capturer=capturer,
    )

    frame1 = capture.capture()
    frame2 = capture.capture()

    assert capturer.regions == [
        {"left": 10, "top": 20, "width": 4, "height": 3},
        {"left": 100, "top": 200, "width": 5, "height": 2},
    ]
    assert frame1.sequence == 1
    assert frame1.width == 4
    assert frame1.height == 3
    assert len(frame1.bgra) == 4 * 3 * 4
    assert frame2.sequence == 2
    assert frame2.window.client_rect.left == 100


def test_capture_rejects_invalid_pixel_buffer_size():
    capture = BalatroScreenCapture(
        tracker=Tracker([window()]),
        capturer=Capturer(fill=b"\x00"),
    )

    with pytest.raises(BalatroCaptureError):
        capture.capture()


def test_capture_closes_underlying_capturer():
    capturer = Capturer()
    capture = BalatroScreenCapture(
        tracker=Tracker([window()]),
        capturer=capturer,
    )

    capture.close()

    assert capturer.closed is True


def test_save_frame_png_writes_png_dimensions(tmp_path):
    capture = BalatroScreenCapture(
        tracker=Tracker([window(width=2, height=3)]),
        capturer=Capturer(fill=b"\x0a\x14\x1e\xff"),
    )
    frame = capture.capture()
    path = save_frame_png(frame, tmp_path / "frame.png")
    data = path.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    assert struct.unpack(">II", data[16:24]) == (2, 3)
