from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any

from games.balatro.live.injected.bridge import default_bridge_dir


AGENT_STATUS_SCHEMA = "balatro-agent-status-v1"
AGENT_TELEMETRY_SCHEMA = "balatro-agent-telemetry-v1"
TELEMETRY_REPLACE_ATTEMPTS = 4
TELEMETRY_REPLACE_BACKOFF_SECONDS = 0.05


def default_agent_control_dir() -> Path:
    return default_bridge_dir().parent / "game-ai-framework-agent"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        get_exit_code = kernel32.GetExitCodeProcess
        get_exit_code.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        get_exit_code.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        handle = open_process(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = wintypes.DWORD()
            if not get_exit_code(handle, ctypes.byref(exit_code)):
                return False
            return int(exit_code.value) == STILL_ACTIVE
        finally:
            close_handle(handle)

    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError, PermissionError):
        return False
    return True


@dataclass
class BalatroAgentControl:
    directory: Path

    def __init__(self, directory: str | Path | None = None):
        self.directory = (
            Path(directory)
            if directory is not None
            else default_agent_control_dir()
        )

    @property
    def pid_path(self) -> Path:
        return self.directory / "agent.pid"

    @property
    def monitor_pid_path(self) -> Path:
        return self.directory / "monitor.pid"

    @property
    def stop_path(self) -> Path:
        return self.directory / "stop.request"

    @property
    def status_path(self) -> Path:
        return self.directory / "status.json"

    @property
    def telemetry_path(self) -> Path:
        return self.directory / "telemetry.json"

    @property
    def start_lock_path(self) -> Path:
        return self.directory / "start.lock"

    def ensure_directory(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def read_pid(self) -> int | None:
        try:
            raw = self.pid_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        try:
            pid = int(raw)
        except ValueError:
            return None
        return pid if pid > 0 else None

    def running_pid(self) -> int | None:
        pid = self.read_pid()
        if pid is None:
            return None
        if _process_is_running(pid):
            return pid
        self.clear_pid(expected_pid=pid)
        return None

    def read_monitor_pid(self) -> int | None:
        try:
            raw = self.monitor_pid_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        try:
            pid = int(raw)
        except ValueError:
            return None
        return pid if pid > 0 else None

    def running_monitor_pid(self) -> int | None:
        pid = self.read_monitor_pid()
        if pid is None:
            return None
        if _process_is_running(pid):
            return pid
        self.clear_monitor_pid(expected_pid=pid)
        return None

    def claim_monitor_process(self, pid: int | None = None) -> int:
        self.ensure_directory()
        actual_pid = int(os.getpid() if pid is None else pid)
        existing = self.running_monitor_pid()
        if existing is not None and existing != actual_pid:
            raise RuntimeError(
                f"Balatro live monitor is already running as PID {existing}"
            )
        self.monitor_pid_path.write_text(str(actual_pid), encoding="utf-8")
        return actual_pid

    def clear_monitor_pid(self, *, expected_pid: int | None = None) -> None:
        if expected_pid is not None:
            current = self.read_monitor_pid()
            if current is not None and current != int(expected_pid):
                return
        try:
            self.monitor_pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    def claim_current_process(self, pid: int | None = None) -> int:
        self.ensure_directory()
        actual_pid = int(os.getpid() if pid is None else pid)
        existing = self.running_pid()
        if existing is not None and existing != actual_pid:
            raise RuntimeError(
                f"Balatro agent is already running as PID {existing}"
            )
        self.pid_path.write_text(str(actual_pid), encoding="utf-8")
        self.clear_stop_request()
        self.release_start_lock()
        return actual_pid

    def clear_pid(self, *, expected_pid: int | None = None) -> None:
        if expected_pid is not None:
            current = self.read_pid()
            if current is not None and current != int(expected_pid):
                return
        try:
            self.pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    def request_stop(self) -> None:
        self.ensure_directory()
        self.stop_path.write_text(_utc_now(), encoding="utf-8")

    def stop_requested(self) -> bool:
        return self.stop_path.exists()

    def clear_stop_request(self) -> None:
        try:
            self.stop_path.unlink(missing_ok=True)
        except OSError:
            pass

    def acquire_start_lock(self) -> bool:
        self.ensure_directory()
        try:
            descriptor = os.open(
                self.start_lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            return False
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(_utc_now())
        return True

    def release_start_lock(self) -> None:
        try:
            self.start_lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        """Atomically write correctness-relevant control state.

        Status callers deliberately retain fail-fast semantics. Monitor-only
        telemetry uses its own best-effort writer below so a telemetry file lock
        cannot weaken the durability contract of status or session state.
        """
        self.ensure_directory()
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _write_telemetry_json(self, payload: dict[str, Any]) -> bool:
        """Best-effort atomic telemetry write resilient to transient Windows locks."""
        self.ensure_directory()
        path = self.telemetry_path
        temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            for attempt in range(TELEMETRY_REPLACE_ATTEMPTS):
                try:
                    os.replace(temporary, path)
                    return True
                except PermissionError:
                    if attempt + 1 >= TELEMETRY_REPLACE_ATTEMPTS:
                        return False
                    sleep(TELEMETRY_REPLACE_BACKOFF_SECONDS * (attempt + 1))
                except OSError:
                    return False
            return False
        except (OSError, TypeError, ValueError):
            return False
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def write_status(self, state: str, **data: Any) -> None:
        self._write_json(
            self.status_path,
            {
                "schema": AGENT_STATUS_SCHEMA,
                "state": str(state),
                "updated_at": _utc_now(),
                **data,
            },
        )

    def read_status(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if payload.get("schema") != AGENT_STATUS_SCHEMA:
            return {}
        return payload

    def write_telemetry(self, activity: str, **data: Any) -> None:
        self._write_telemetry_json(
            {
                "schema": AGENT_TELEMETRY_SCHEMA,
                "activity": str(activity),
                "updated_at": _utc_now(),
                **data,
            }
        )

    def read_telemetry(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.telemetry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if payload.get("schema") != AGENT_TELEMETRY_SCHEMA:
            return {}
        return payload

    def clear_telemetry(self) -> None:
        try:
            self.telemetry_path.unlink(missing_ok=True)
        except OSError:
            pass

    def mark_off(self, *, reason: str, **data: Any) -> None:
        # Telemetry is monitor-only and intentionally nonfatal. Status remains the
        # authoritative control record and keeps its normal fail-fast write path.
        self.write_telemetry("OFF", reason=str(reason), **data)
        self.write_status("OFF", reason=str(reason), **data)
        self.clear_stop_request()
        self.clear_pid()
        self.release_start_lock()
