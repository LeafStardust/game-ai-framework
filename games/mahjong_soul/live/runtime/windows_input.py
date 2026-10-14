"""Windows mouse backend; requires the Steam game to already be foreground."""

import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import PureWindowsPath


class WindowsMouse:
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows input requires Windows")
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = w.HWND
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

    def click(self, x, y, width, height):
        previous = self.user.SetThreadDpiAwarenessContext(w.HANDLE(-4))
        if not previous:
            raise c.WinError(c.get_last_error())
        try:
            hwnd = self._foreground()
            rect, origin = w.RECT(), w.POINT()
            if not self.user.GetClientRect(hwnd, c.byref(rect)) or not self.user.ClientToScreen(hwnd, c.byref(origin)):
                raise c.WinError(c.get_last_error())
            if (rect.right, rect.bottom) != (width, height):
                raise ValueError("Game window size changed; recalibrate")
            px, py = origin.x + round(x * (width - 1)), origin.y + round(y * (height - 1))
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
            inputs = (Input * 3)()
            inputs[0].data.mouse = Mouse(ax, ay, 0, 0x8000 | 0x4000 | 1, 0, 0)
            inputs[1].data.mouse.dwFlags = 2
            inputs[2].data.mouse.dwFlags = 4
            if self._foreground() != hwnd:
                raise ValueError("Foreground changed before click")
            sent = self.user.SendInput(3, inputs, c.sizeof(Input))
            if sent != 3:
                # Ensure a partially delivered press cannot leave the button held.
                release = Input()
                release.data.mouse.dwFlags = 4
                self.user.SendInput(1, c.byref(release), c.sizeof(Input))
                raise OSError("Mouse input was not fully delivered; do not retry")
        finally:
            self.user.SetThreadDpiAwarenessContext(previous)
