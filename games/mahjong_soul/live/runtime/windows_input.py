"""Windows mouse backend; requires the Steam game to already be foreground."""

import ctypes as c
from ctypes import wintypes as w
import os
import time
from pathlib import PureWindowsPath


class WindowsMouse:
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows input requires Windows")
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = w.HWND
        self.user.IsIconic.argtypes = [w.HWND]
        self.user.IsIconic.restype = w.BOOL
        self.user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
        self.user.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
        self.user.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
        self.user.SetThreadDpiAwarenessContext.argtypes = [w.HANDLE]
        self.user.SetThreadDpiAwarenessContext.restype = w.HANDLE
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]

    def _foreground(self):
        hwnd = self.user.GetForegroundWindow()
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
        handle = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not handle:
            raise OSError("Cannot inspect foreground process")
        try:
            name, size = c.create_unicode_buffer(32768), w.DWORD(32768)
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, name, c.byref(size)):
                raise c.WinError(c.get_last_error())
            if PureWindowsPath(name.value).name.lower() != "jantama_mahjongsoul.exe":
                raise ValueError("Mahjong Soul is not the foreground window")
        finally:
            self.kernel.CloseHandle(handle)
        return hwnd

    def _client_geometry(self, hwnd):
        if self.user.IsIconic(hwnd):
            raise ValueError("Game window is minimized")
        rect, origin = w.RECT(), w.POINT()
        if not self.user.GetClientRect(hwnd, c.byref(rect)) or not self.user.ClientToScreen(hwnd, c.byref(origin)):
            raise c.WinError(c.get_last_error())
        if rect.right <= 1 or rect.bottom <= 1:
            raise ValueError("Game client has no usable area")
        return {"width": rect.right, "height": rect.bottom, "left": origin.x, "top": origin.y}

    def client_geometry(self):
        """Read the foreground game's physical client dimensions without input."""
        previous = self.user.SetThreadDpiAwarenessContext(w.HANDLE(-4))
        if not previous:
            raise c.WinError(c.get_last_error())
        try:
            hwnd = self._foreground()
            result = self._client_geometry(hwnd)
            if self._foreground() != hwnd:
                raise ValueError("Foreground changed during geometry inspection")
            return result
        finally:
            self.user.SetThreadDpiAwarenessContext(previous)

    def click(self, x, y, width, height):
        self._clicks(x, y, width, height, 1)

    def double_click(self, x, y, width, height):
        """Two frame-spaced clicks; each press/release is a separate OS event."""
        self._clicks(x, y, width, height, 2)

    def park(self, width, height):
        """Move off the hand without pressing any button."""
        self._clicks(.72,.45,width,height,0)

    def _clicks(self, x, y, width, height, count):
        previous = self.user.SetThreadDpiAwarenessContext(w.HANDLE(-4))
        if not previous:
            raise c.WinError(c.get_last_error())
        try:
            hwnd = self._foreground()
            geometry = self._client_geometry(hwnd)
            if (geometry["width"], geometry["height"]) != (width, height):
                raise ValueError("Game window size changed; select a calibrated size profile")
            px = geometry["left"] + round(x * (width - 1))
            py = geometry["top"] + round(y * (height - 1))
            vx, vy = self.user.GetSystemMetrics(76), self.user.GetSystemMetrics(77)
            vw, vh = self.user.GetSystemMetrics(78), self.user.GetSystemMetrics(79)
            if not (vx <= px < vx + vw and vy <= py < vy + vh):
                raise ValueError("Click lies outside the virtual desktop")
            class Mouse(c.Structure):
                _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("mouseData", w.DWORD),
                            ("dwFlags", w.DWORD), ("time", w.DWORD), ("extra", c.c_size_t)]
            class Keyboard(c.Structure):
                _fields_ = [("vk", w.WORD), ("scan", w.WORD), ("flags", w.DWORD),
                            ("time", w.DWORD), ("extra", c.c_size_t)]
            class Data(c.Union):
                _fields_ = [("mouse", Mouse), ("keyboard", Keyboard)]
            class Input(c.Structure):
                _fields_ = [("type", w.DWORD), ("data", Data)]
            self.user.SendInput.argtypes = [w.UINT, c.POINTER(Input), c.c_int]
            self.user.SendInput.restype = w.UINT
            ax = round((px - vx) * 65535 / (vw - 1))
            ay = round((py - vy) * 65535 / (vh - 1))
            def check_window():
                if self._foreground() != hwnd:
                    raise ValueError("Foreground changed before click")
                if self._client_geometry(hwnd) != geometry:
                    raise ValueError("Game window moved or resized before click; rebuild the plan")

            def send(flags):
                event = Input()
                event.data.mouse = Mouse(ax, ay, 0, flags, 0, 0)
                if self.user.SendInput(1, c.byref(event), c.sizeof(Input)) != 1:
                    raise OSError("Mouse input was not fully delivered; do not retry")

            move = 0x8000 | 0x4000 | 1
            if count == 0:
                check_window()
                send(move)
                return
            for index in range(count):
                check_window()
                send(move)
                # Give the client a frame at the target before pressing. A
                # single SendInput batch can collapse down/up into one frame.
                time.sleep(.04)
                check_window()
                release_needed = True
                try:
                    send(move | 2)
                    time.sleep(.08)
                    check_window()
                    send(4)
                    release_needed = False
                finally:
                    if release_needed:
                        # Always release an uncertain/held button, even after
                        # focus loss. Never retry the actual click.
                        try: send(4)
                        except OSError: pass
                # Keep the cursor at the target while the release is consumed.
                # Otherwise the caller's immediate park can steal the click.
                time.sleep(.08)
        finally:
            self.user.SetThreadDpiAwarenessContext(previous)
