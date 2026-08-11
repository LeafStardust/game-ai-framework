from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from ctypes import wintypes
from typing import Iterator

from .window import BalatroWindowLocator


class BalatroProcessMemoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class MemoryRegion:
    base: int
    size: int
    state: int
    protect: int
    kind: int

    @property
    def end(self) -> int:
        return self.base + self.size


class _MemoryBasicInformation(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


class WindowsProcessMemoryReader:
    """Read-only Windows process-memory access for the running Balatro process.

    This module intentionally uses only the Python standard library and Win32
    APIs. It does not inject code, allocate remote memory, write process memory,
    or depend on a third-party mod/runtime.
    """

    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    MEM_COMMIT = 0x1000
    PAGE_NOACCESS = 0x01
    PAGE_GUARD = 0x100

    def __init__(self, pid: int, handle: int):
        self.pid = int(pid)
        self.handle = int(handle)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    @classmethod
    def from_balatro_window(
        cls,
        locator: BalatroWindowLocator | None = None,
    ) -> "WindowsProcessMemoryReader":
        if platform.system() != "Windows":
            raise BalatroProcessMemoryError(
                "Balatro process-memory observation currently requires Windows"
            )

        locator = locator or BalatroWindowLocator()
        window = locator.find()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        pid = wintypes.DWORD()
        thread_id = user32.GetWindowThreadProcessId(
            wintypes.HWND(window.handle),
            ctypes.byref(pid),
        )
        if not thread_id or not pid.value:
            raise BalatroProcessMemoryError(
                "unable to resolve Balatro process id from its window"
            )

        access = cls.PROCESS_VM_READ | cls.PROCESS_QUERY_INFORMATION
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        process = kernel32.OpenProcess(access, False, pid.value)
        if not process:
            error = ctypes.get_last_error()
            raise BalatroProcessMemoryError(
                f"unable to open Balatro process {pid.value} for read-only access "
                f"(WinError {error})"
            )

        return cls(pid.value, int(process))

    def close(self) -> None:
        if not self.handle:
            return
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.CloseHandle(wintypes.HANDLE(self.handle))
        self.handle = 0

    def read(self, address: int, size: int) -> bytes:
        if not self.handle:
            raise BalatroProcessMemoryError("Balatro process handle is closed")
        if address < 0 or size < 0:
            raise ValueError("address and size must be non-negative")
        if size == 0:
            return b""

        self._kernel32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self._kernel32.ReadProcessMemory.restype = wintypes.BOOL

        buffer = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        ok = self._kernel32.ReadProcessMemory(
            wintypes.HANDLE(self.handle),
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(read),
        )
        if not ok:
            error = ctypes.get_last_error()
            raise BalatroProcessMemoryError(
                f"ReadProcessMemory failed at 0x{address:x} for {size} bytes "
                f"(WinError {error})"
            )
        return bytes(buffer.raw[: read.value])

    def regions(self) -> tuple[MemoryRegion, ...]:
        if not self.handle:
            raise BalatroProcessMemoryError("Balatro process handle is closed")

        self._kernel32.VirtualQueryEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(_MemoryBasicInformation),
            ctypes.c_size_t,
        ]
        self._kernel32.VirtualQueryEx.restype = ctypes.c_size_t

        result: list[MemoryRegion] = []
        address = 0
        max_address = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
        mbi = _MemoryBasicInformation()

        while address < max_address:
            queried = self._kernel32.VirtualQueryEx(
                wintypes.HANDLE(self.handle),
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi),
            )
            if not queried:
                break

            base = int(mbi.BaseAddress or 0)
            size = int(mbi.RegionSize)
            if size <= 0:
                break

            result.append(
                MemoryRegion(
                    base=base,
                    size=size,
                    state=int(mbi.State),
                    protect=int(mbi.Protect),
                    kind=int(mbi.Type),
                )
            )
            next_address = base + size
            if next_address <= address:
                break
            address = next_address

        return tuple(result)

    def readable_regions(self) -> tuple[MemoryRegion, ...]:
        return tuple(
            region
            for region in self.regions()
            if region.state == self.MEM_COMMIT
            and not (region.protect & self.PAGE_GUARD)
            and not (region.protect & self.PAGE_NOACCESS)
        )

    def iter_readable_chunks(
        self,
        *,
        chunk_size: int = 1024 * 1024,
        overlap: int = 0,
    ) -> Iterator[tuple[int, bytes]]:
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be between zero and chunk_size - 1")

        step = chunk_size - overlap
        for region in self.readable_regions():
            offset = 0
            while offset < region.size:
                size = min(chunk_size, region.size - offset)
                address = region.base + offset
                try:
                    data = self.read(address, size)
                except BalatroProcessMemoryError:
                    # VirtualQueryEx can race a live allocator. A failed chunk is
                    # skipped rather than weakening read-only guarantees or aborting
                    # an otherwise useful scan.
                    offset += step
                    continue
                if data:
                    yield address, data
                offset += step

    def find_bytes(
        self,
        needle: bytes,
        *,
        max_matches: int = 256,
        chunk_size: int = 1024 * 1024,
    ) -> tuple[int, ...]:
        """Find byte-pattern addresses across readable committed memory.

        Scanning is bounded by ``max_matches`` and handles patterns crossing chunk
        boundaries by overlapping each read by ``len(needle)-1`` bytes.
        """

        if not needle:
            raise ValueError("needle cannot be empty")
        if max_matches < 1:
            raise ValueError("max_matches must be positive")
        if chunk_size <= len(needle):
            chunk_size = len(needle) + 1

        matches: list[int] = []
        seen: set[int] = set()
        overlap = len(needle) - 1
        for base, data in self.iter_readable_chunks(
            chunk_size=chunk_size,
            overlap=overlap,
        ):
            start = 0
            while True:
                index = data.find(needle, start)
                if index < 0:
                    break
                address = base + index
                if address not in seen:
                    seen.add(address)
                    matches.append(address)
                    if len(matches) >= max_matches:
                        return tuple(matches)
                start = index + 1
        return tuple(matches)

    def __enter__(self) -> "WindowsProcessMemoryReader":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
