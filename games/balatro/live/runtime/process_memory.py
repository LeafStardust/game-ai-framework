from __future__ import annotations

import ctypes
import multiprocessing as mp
import platform
import time
from dataclasses import dataclass
from ctypes import wintypes
from queue import Empty
from typing import Iterator


DEFAULT_WINDOWS_READ_TIMEOUT_SECONDS = 5.0


def _sleep_for_test(seconds: float) -> None:
    time.sleep(seconds)


def _read_process_memory_bytes(pid: int, address: int, size: int) -> bytes:
    """Open a fresh read-only handle and execute the Win32 read in a child process."""
    if pid <= 0 or address < 0 or size < 0:
        raise ValueError("pid/address/size must be valid")
    if size == 0:
        return b""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    read_process_memory = kernel32.ReadProcessMemory
    read_process_memory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    read_process_memory.restype = wintypes.BOOL

    access = 0x0010 | 0x0400
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    process = kernel32.OpenProcess(access, False, pid)
    if not process:
        error = ctypes.get_last_error()
        raise BalatroProcessMemoryError(
            f"unable to open process {pid} for read-only access (WinError {error})"
        )
    try:
        buffer = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        ok = read_process_memory(
            wintypes.HANDLE(process),
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
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(process))


def _run_process_timeout_worker(queue, func, args) -> None:
    try:
        queue.put(("ok", func(*args)))
    except BaseException as exc:  # pragma: no cover - exercised by timeout test
        queue.put(("error", repr(exc)))


def _run_with_process_timeout(func, *, timeout_seconds: float, args=None) -> object:
    """Execute a blocking callable in a worker process with a bounded lifetime.

    This avoids the unsafe pattern of trying to kill a Python thread that has
    entered a blocking native Win32 call. If the worker exceeds the timeout it is
    terminated, and the caller sees a fail-closed BalatroProcessMemoryError.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    args = () if args is None else tuple(args)
    context = mp.get_context("spawn")
    queue = context.Queue()
    worker = context.Process(
        target=_run_process_timeout_worker,
        args=(queue, func, args),
        daemon=True,
    )
    worker.start()
    worker.join(timeout_seconds)
    if worker.is_alive():
        worker.terminate()
        worker.join(1)
        if worker.is_alive():
            worker.kill()
        raise BalatroProcessMemoryError(
            f"blocking Win32 process call timed out after {timeout_seconds} seconds"
        )

    try:
        status, payload = queue.get(timeout=1)
    except Empty as exc:
        raise BalatroProcessMemoryError(
            f"blocking Win32 process call did not return before {timeout_seconds} seconds"
        ) from exc
    if status == "error":
        raise BalatroProcessMemoryError(str(payload))
    return payload

from .process_locator import BalatroWindowLocator


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

        self._read_process_memory = self._kernel32.ReadProcessMemory
        self._read_process_memory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self._read_process_memory.restype = wintypes.BOOL

        self._virtual_query_ex = self._kernel32.VirtualQueryEx
        self._virtual_query_ex.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(_MemoryBasicInformation),
            ctypes.c_size_t,
        ]
        self._virtual_query_ex.restype = ctypes.c_size_t

        self._close_handle = self._kernel32.CloseHandle
        self._close_handle.argtypes = [wintypes.HANDLE]
        self._close_handle.restype = wintypes.BOOL

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
        self._close_handle(wintypes.HANDLE(self.handle))
        self.handle = 0

    def read(
        self,
        address: int,
        size: int,
        *,
        timeout_seconds: float | None = DEFAULT_WINDOWS_READ_TIMEOUT_SECONDS,
    ) -> bytes:
        if not self.handle:
            raise BalatroProcessMemoryError("Balatro process handle is closed")
        if address < 0 or size < 0:
            raise ValueError("address and size must be non-negative")
        if size == 0:
            return b""

        if timeout_seconds is None:
            return self._read_once(address, size)
        return _run_with_process_timeout(
            _read_process_memory_bytes,
            timeout_seconds=timeout_seconds,
            args=(self.pid, address, size),
        )

    def _read_once(self, address: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        ok = self._read_process_memory(
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

        result: list[MemoryRegion] = []
        address = 0
        max_address = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
        mbi = _MemoryBasicInformation()

        while address < max_address:
            queried = self._virtual_query_ex(
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
