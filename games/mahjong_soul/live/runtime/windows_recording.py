"""Read-only Windows client capture and mouse-button sampling; no input injection."""
import ctypes as c
from ctypes import wintypes as w
import struct
import zlib

from games.mahjong_soul.live.runtime.windows_input import WindowsMouse


def png_from_bgra(pixels, width, height):
    rgb = bytearray(width * height * 3)
    rgb[0::3] = pixels[2::4]; rgb[1::3] = pixels[1::4]; rgb[2::3] = pixels[0::4]
    stride = width * 3
    raw = b"".join(b"\0" + rgb[i:i+stride] for i in range(0, len(rgb), stride))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind+data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 3)) + chunk(b"IEND", b""))


class WindowsRecorder:
    def __init__(self):
        self.mouse = WindowsMouse()
        self.user = self.mouse.user
        self.gdi = c.WinDLL("gdi32", use_last_error=True)
        self.user.GetAsyncKeyState.argtypes = [c.c_int]
        self.user.GetAsyncKeyState.restype = c.c_short
        self.user.GetCursorPos.argtypes = [c.POINTER(w.POINT)]
        self.user.GetDC.argtypes = [w.HWND]; self.user.GetDC.restype = w.HDC
        self.user.ReleaseDC.argtypes = [w.HWND, w.HDC]
        self.gdi.CreateCompatibleDC.argtypes = [w.HDC]; self.gdi.CreateCompatibleDC.restype = w.HDC
        self.gdi.CreateCompatibleBitmap.argtypes = [w.HDC, c.c_int, c.c_int]
        self.gdi.CreateCompatibleBitmap.restype = w.HBITMAP
        self.gdi.SelectObject.argtypes = [w.HDC, w.HANDLE]; self.gdi.SelectObject.restype = w.HANDLE
        self.gdi.DeleteObject.argtypes = [w.HANDLE]
        self.gdi.DeleteDC.argtypes = [w.HDC]
        self.gdi.BitBlt.argtypes = [w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.HDC,c.c_int,c.c_int,w.DWORD]
        self.gdi.GetDIBits.argtypes = [w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
        self.down = bool(self.user.GetAsyncKeyState(1) & 0x8000)

    def poll(self):
        down = bool(self.user.GetAsyncKeyState(1) & 0x8000)
        pressed = down and not self.down
        self.down = down
        previous = self.user.SetThreadDpiAwarenessContext(w.HANDLE(-4))
        if not previous: return None
        try:
            hwnd = self.mouse._foreground()
            geometry = self.mouse._client_geometry(hwnd)
            point = w.POINT()
            if not self.user.GetCursorPos(c.byref(point)): return None
            x, y = point.x-geometry["left"], point.y-geometry["top"]
            pressed = pressed and 0 <= x < geometry["width"] and 0 <= y < geometry["height"]
            if self.mouse._foreground() != hwnd: return None
            return geometry, pressed, x, y
        except (ValueError, OSError):
            return None
        finally:
            self.user.SetThreadDpiAwarenessContext(previous)

    def geometry(self):
        try: return self.mouse.client_geometry()
        except (ValueError, OSError): return None

    def frame(self, geometry):
        previous = self.user.SetThreadDpiAwarenessContext(w.HANDLE(-4))
        if not previous: return None
        screen = memory = bitmap = old = None
        try:
            hwnd = self.mouse._foreground()
            if self.mouse._client_geometry(hwnd) != geometry: return None
            width, height = geometry["width"], geometry["height"]
            # Refuse partially off-screen clients instead of capturing unrelated pixels.
            vx, vy = self.user.GetSystemMetrics(76), self.user.GetSystemMetrics(77)
            vw, vh = self.user.GetSystemMetrics(78), self.user.GetSystemMetrics(79)
            if not (vx <= geometry["left"] and vy <= geometry["top"]
                    and geometry["left"]+width <= vx+vw and geometry["top"]+height <= vy+vh): return None
            screen = self.user.GetDC(None)
            memory = self.gdi.CreateCompatibleDC(screen)
            bitmap = self.gdi.CreateCompatibleBitmap(screen, width, height)
            if not screen or not memory or not bitmap: raise OSError("Cannot allocate screenshot")
            old = self.gdi.SelectObject(memory, bitmap)
            if not self.gdi.BitBlt(memory,0,0,width,height,screen,geometry["left"],geometry["top"],0x00CC0020):
                raise OSError("Cannot capture game client")
            self.gdi.SelectObject(memory, old); old = None
            header = c.create_string_buffer(struct.pack("<IiiHHIIiiII",40,width,-height,1,32,0,width*height*4,0,0,0,0),40)
            pixels = c.create_string_buffer(width*height*4)
            if self.gdi.GetDIBits(memory,bitmap,0,height,pixels,header,0) != height:
                raise OSError("Cannot read screenshot pixels")
            if self.mouse._foreground() != hwnd or self.mouse._client_geometry(hwnd) != geometry: return None
            return png_from_bgra(pixels.raw,width,height)
        except (ValueError, OSError):
            return None
        finally:
            if old and memory: self.gdi.SelectObject(memory, old)
            if bitmap: self.gdi.DeleteObject(bitmap)
            if memory: self.gdi.DeleteDC(memory)
            if screen: self.user.ReleaseDC(None, screen)
            self.user.SetThreadDpiAwarenessContext(previous)
