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
    SW_RESTORE = 9

    def __init__(
        self,
        *,
        user32=None,
        kernel32=None,
        focus_retries: int = 3,
        focus_retry_delay: float = 0.05,
    ):
        injected = user32 is not None or kernel32 is not None
        if not injected and platform.system() != "Windows":
            raise MouseControlError("Windows mouse control requires Windows")
        if (user32 is None) != (kernel32 is None):
            raise ValueError("user32 and kernel32 must be supplied together")

        if user32 is None:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
        self.user32 = user32
        self.kernel32 = kernel32
        self.focus_retries = max(1, int(focus_retries))
        self.focus_retry_delay = max(0.0, float(focus_retry_delay))

        try:
            self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        except (AttributeError, TypeError):
            pass
        try:
            self.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    def focus(self, handle: int) -> None:
        handle = int(handle)
        if handle <= 0:
            raise MouseControlError(f"invalid Balatro window handle: {handle}")
        if self._foreground_handle() == handle:
            return

        hwnd = ctypes.c_void_p(handle)
        is_window = getattr(self.user32, "IsWindow", None)
        if callable(is_window) and not is_window(hwnd):
            raise MouseControlError(
                f"Balatro window handle is no longer available: {handle}"
            )

        is_iconic = getattr(self.user32, "IsIconic", None)
        if callable(is_iconic) and is_iconic(hwnd):
            show_window_async = getattr(self.user32, "ShowWindowAsync", None)
            if callable(show_window_async):
                show_window_async(hwnd, self.SW_RESTORE)

        for attempt in range(self.focus_retries):
            self._request_foreground(hwnd)
            if self._foreground_handle() == handle:
                return
            if attempt + 1 < self.focus_retries and self.focus_retry_delay > 0:
                time.sleep(self.focus_retry_delay)

        raise MouseControlError(
            "unable to focus Balatro window handle after foreground recovery: "
            f"{handle}"
        )

    def _foreground_handle(self) -> int:
        return int(self.user32.GetForegroundWindow() or 0)

    def _request_foreground(self, hwnd) -> None:
        """Try normal focus first, then temporarily join Windows input queues."""
        bring_to_top = getattr(self.user32, "BringWindowToTop", None)
        if callable(bring_to_top):
            bring_to_top(hwnd)
        self.user32.SetForegroundWindow(hwnd)
        if self._foreground_handle() == int(hwnd.value or 0):
            return

        attach_thread_input = getattr(self.user32, "AttachThreadInput", None)
        get_window_thread = getattr(self.user32, "GetWindowThreadProcessId", None)
        get_current_thread = getattr(self.kernel32, "GetCurrentThreadId", None)
        if not (
            callable(attach_thread_input)
            and callable(get_window_thread)
            and callable(get_current_thread)
        ):
            return

        current_thread = int(get_current_thread() or 0)
        foreground = self._foreground_handle()
        foreground_thread = (
            int(get_window_thread(ctypes.c_void_p(foreground), None) or 0)
            if foreground
            else 0
        )
        target_thread = int(get_window_thread(hwnd, None) or 0)

        attached: list[int] = []
        for thread_id in (foreground_thread, target_thread):
            if (
                thread_id
                and current_thread
                and thread_id != current_thread
                and thread_id not in attached
                and attach_thread_input(current_thread, thread_id, True)
            ):
                attached.append(thread_id)

        try:
            if callable(bring_to_top):
                bring_to_top(hwnd)
            self.user32.SetForegroundWindow(hwnd)
        finally:
            for thread_id in reversed(attached):
                attach_thread_input(current_thread, thread_id, False)

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
        hover_delay: float = 0.10,
    ):
        self.provider = provider or WindowsMouseInputProvider()
        self.armed = armed
        self.hover_delay = max(0.0, hover_delay)

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
        hover_delay: float | None = None,
    ) -> None:
        self._require_armed()
        if count < 1:
            raise ValueError("mouse click count must be at least 1")

        if window is not None:
            self.provider.focus(window.handle)
        self.provider.move_to(point.x, point.y)

        settle = self.hover_delay if hover_delay is None else max(0.0, hover_delay)
        if settle > 0:
            time.sleep(settle)

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
        hover_delay: float | None = None,
    ) -> None:
        self.click_screen(
            viewport.screen_point(point),
            window=viewport.frame.window,
            count=count,
            interval=interval,
            hover_delay=hover_delay,
        )

    def click_rect(
        self,
        viewport: BalatroViewport,
        rect: NormalizedRect,
        *,
        count: int = 1,
        interval: float = 0.05,
        hover_delay: float | None = None,
    ) -> None:
        self.click(
            viewport,
            rect.center,
            count=count,
            interval=interval,
            hover_delay=hover_delay,
        )

    def _require_armed(self) -> None:
        if not self.armed:
            raise MouseControlNotArmed(
                "Balatro mouse control is disarmed; call arm() before sending input"
            )
