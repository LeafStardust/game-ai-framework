from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass


class BalatroProcessLocatorError(RuntimeError):
    pass


class BalatroProcessNotFound(BalatroProcessLocatorError):
    pass


@dataclass(frozen=True)
class BalatroProcessWindow:
    """Minimal visible-window identity used only to resolve Balatro's PID."""

    handle: int
    title: str


class BalatroWindowLocator:
    """Locate Balatro's visible HWND without any UI-control responsibilities."""

    def __init__(self, title: str = "Balatro") -> None:
        if platform.system() != "Windows":
            raise BalatroProcessLocatorError(
                "Balatro process discovery currently requires Windows"
            )
        self.title = str(title)
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)

    def find(self) -> BalatroProcessWindow:
        matches: list[BalatroProcessWindow] = []
        callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

        @callback_type(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def callback(hwnd, _lparam):
            handle = int(hwnd)
            if not self.user32.IsWindowVisible(ctypes.c_void_p(handle)):
                return True

            length = int(self.user32.GetWindowTextLengthW(ctypes.c_void_p(handle)))
            if length <= 0:
                return True

            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(
                ctypes.c_void_p(handle),
                buffer,
                len(buffer),
            )
            title = buffer.value.strip()
            if title and self.title.casefold() in title.casefold():
                matches.append(BalatroProcessWindow(handle=handle, title=title))
            return True

        if not self.user32.EnumWindows(callback, 0):
            error = ctypes.get_last_error()
            raise BalatroProcessLocatorError(
                f"unable to enumerate Windows windows (WinError {error})"
            )

        if not matches:
            raise BalatroProcessNotFound(
                f"unable to find a visible {self.title} window"
            )

        exact = self.title.casefold()
        matches.sort(
            key=lambda window: window.title.casefold() == exact,
            reverse=True,
        )
        return matches[0]
