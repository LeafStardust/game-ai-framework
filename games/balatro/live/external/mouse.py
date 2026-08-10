from __future__ import annotations

import ctypes
import platform
import time
from typing import Protocol

from .viewport import (
    BalatroViewport,
    NormalizedPoint,
    NormalizedRect,
    PixelPoint,
)
from .window import BalatroWindow


class MouseControlError(RuntimeError):
    pass


class MouseControlNotArmed(MouseControlError):
    pass


class MouseInputProvider(Protocol):

    def focus(self, handle: int) -> None: ...

    def move_to(self, x: int, y: int) -> None: ...

    def left_down(self) -> None: ...

    def left_up(self) -> None: ...


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("data", _InputUnion),
    ]


class WindowsMouseInputProvider:
    """Sends normal desktop mouse input through the Windows user32 API."""

    INPUT_MOUSE = 0
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004

    def __init__(self):
        if platform.system() != "Windows":
            raise MouseControlError("Windows mouse control requires Windows")
        self.user32 = ctypes.windll.user32
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        try:
            self.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    def focus(self, handle: int) -> None:
        foreground = int(self.user32.GetForegroundWindow() or 0)
        if foreground == handle:
            return
        if not self.user32.SetForegroundWindow(ctypes.c_void_p(handle)):
            raise MouseControlError(
                f"unable to focus Balatro window handle: {handle}"
            )

    def move_to(self, x: int, y: int) -> None:
        if not self.user32.SetCursorPos(int(x), int(y)):
            raise MouseControlError(
                f"unable to move mouse cursor to ({x}, {y})"
            )

    def left_down(self) -> None:
        self._send_mouse(self.MOUSEEVENTF_LEFTDOWN)

    def left_up(self) -> None:
        self._send_mouse(self.MOUSEEVENTF_LEFTUP)

    def _send_mouse(self, flags: int) -> None:
        event = _Input(
            type=self.INPUT_MOUSE,
            mi=_MouseInput(dwFlags=flags),
        )
        sent = self.user32.SendInput(
            1,
            ctypes.byref(event),
            ctypes.sizeof(_Input),
        )
        if sent != 1:
            raise MouseControlError("Windows SendInput failed")


class BalatroMouseController:
    """Maps normalized Balatro UI targets to the real desktop mouse."""

    def __init__(
        self,
        provider: MouseInputProvider | None = None,
        *,
        armed: bool = False,
    ):
        self.provider = provider or WindowsMouseInputProvider()
        self.armed = armed

    def arm(self) -> None:
        self.armed = True

    def disarm(self) -> None:
        self.armed = False

    def focus(self, window: BalatroWindow) -> None:
        self._require_armed()
        self.provider.focus(window.handle)

    def move_screen(self, point: PixelPoint) -> None:
        self._require_armed()
        self.provider.move_to(point.x, point.y)

    def click_screen(
        self,
        point: PixelPoint,
        *,
        window: BalatroWindow | None = None,
        count: int = 1,
        interval: float = 0.05,
    ) -> None:
        self._require_armed()
        if count < 1:
            raise ValueError("mouse click count must be at least 1")

        if window is not None:
            self.provider.focus(window.handle)
        self.provider.move_to(point.x, point.y)

        for index in range(count):
            self.provider.left_down()
            self.provider.left_up()
            if index + 1 < count and interval > 0:
                time.sleep(interval)

    def click(
        self,
        viewport: BalatroViewport,
        point: NormalizedPoint,
        *,
        count: int = 1,
        interval: float = 0.05,
    ) -> None:
        self.click_screen(
            viewport.screen_point(point),
            window=viewport.frame.window,
            count=count,
            interval=interval,
        )

    def click_rect(
        self,
        viewport: BalatroViewport,
        rect: NormalizedRect,
        *,
        count: int = 1,
        interval: float = 0.05,
    ) -> None:
        self.click(
            viewport,
            rect.center,
            count=count,
            interval=interval,
        )

    def _require_armed(self) -> None:
        if not self.armed:
            raise MouseControlNotArmed(
                "Balatro mouse control is disarmed; call arm() before sending input"
            )
