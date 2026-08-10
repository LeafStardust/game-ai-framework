from __future__ import annotations

import ctypes
import platform
import time
from dataclasses import dataclass
from typing import Protocol


class BalatroWindowError(RuntimeError):
    pass


class BalatroWindowNotFound(BalatroWindowError):
    pass


class BalatroWindowNotForeground(BalatroWindowError):
    pass


@dataclass(frozen=True)
class WindowRect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class BalatroWindow:
    handle: int
    title: str
    client_rect: WindowRect


class WindowProvider(Protocol):

    def list_windows(self) -> list[BalatroWindow]: ...

    def get_window(self, handle: int) -> BalatroWindow | None: ...

    def get_foreground_handle(self) -> int | None: ...


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class WindowsWindowProvider:
    """Reads visible top-level Windows windows through user32."""

    def __init__(self):
        if platform.system() != "Windows":
            raise BalatroWindowError(
                "Windows Balatro window discovery requires Windows"
            )
        self.user32 = ctypes.windll.user32
        try:
            self.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p

    def list_windows(self) -> list[BalatroWindow]:
        windows: list[BalatroWindow] = []
        callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

        @callback_type(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def callback(hwnd, _):
            window = self.get_window(int(hwnd))
            if window is not None:
                windows.append(window)
            return True

        if not self.user32.EnumWindows(callback, 0):
            raise BalatroWindowError("unable to enumerate Windows windows")
        return windows

    def get_window(self, handle: int) -> BalatroWindow | None:
        hwnd = ctypes.c_void_p(handle)
        if not self.user32.IsWindow(hwnd):
            return None
        if not self.user32.IsWindowVisible(hwnd):
            return None

        title_length = self.user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0:
            return None

        buffer = ctypes.create_unicode_buffer(title_length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        title = buffer.value.strip()
        if not title:
            return None

        rect = _Rect()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None

        origin = _Point(rect.left, rect.top)
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            return None

        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width <= 0 or height <= 0:
            return None

        return BalatroWindow(
            handle=handle,
            title=title,
            client_rect=WindowRect(
                left=int(origin.x),
                top=int(origin.y),
                width=width,
                height=height,
            ),
        )

    def get_foreground_handle(self) -> int | None:
        handle = self.user32.GetForegroundWindow()
        return int(handle) if handle else None


class BalatroWindowLocator:
    """Finds the normal Balatro game window without touching the process."""

    def __init__(
        self,
        provider: WindowProvider | None = None,
        title: str = "Balatro",
    ):
        self.provider = provider or WindowsWindowProvider()
        self.title = title

    def find(self) -> BalatroWindow:
        windows = [
            window
            for window in self.provider.list_windows()
            if self._matches(window.title)
        ]
        if not windows:
            raise BalatroWindowNotFound(
                f"unable to find a visible {self.title} window"
            )

        exact = self.title.casefold()
        windows.sort(
            key=lambda window: (
                window.title.casefold() == exact,
                window.client_rect.area,
            ),
            reverse=True,
        )
        return windows[0]

    def refresh(self, handle: int) -> BalatroWindow:
        window = self.provider.get_window(handle)
        if window is None or not self._matches(window.title):
            raise BalatroWindowNotFound(
                f"Balatro window handle is no longer available: {handle}"
            )
        return window

    def foreground_handle(self) -> int | None:
        return self.provider.get_foreground_handle()

    def wait(
        self,
        timeout: float = 10.0,
        poll_interval: float = 0.1,
    ) -> BalatroWindow:
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                return self.find()
            except BalatroWindowNotFound:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(max(0.0, poll_interval))

    def _matches(self, title: str) -> bool:
        return self.title.casefold() in title.casefold()


class BalatroWindowTracker:
    """Keeps the current Balatro client rectangle updated as it moves/resizes."""

    def __init__(self, locator: BalatroWindowLocator | None = None):
        self.locator = locator or BalatroWindowLocator()
        self.current: BalatroWindow | None = None

    def locate(self) -> BalatroWindow:
        self.current = self.locator.find()
        return self.current

    def snapshot(self) -> BalatroWindow:
        if self.current is None:
            return self.locate()

        try:
            self.current = self.locator.refresh(self.current.handle)
        except BalatroWindowNotFound:
            self.current = self.locator.find()
        return self.current

    def require_foreground(self) -> BalatroWindow:
        window = self.snapshot()
        foreground = self.locator.foreground_handle()
        if foreground != window.handle:
            raise BalatroWindowNotForeground(
                "Balatro must be the foreground window before external capture"
            )
        return window
