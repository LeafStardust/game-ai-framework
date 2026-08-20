from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import agent_control as agent_control_module
from .agent_control import BalatroAgentControl


SUPERVISOR_MODULE = "games.balatro.live.runtime.balatro_agent_supervisor_entry"
MONITOR_MODULE = "games.balatro.live.runtime.balatro_agent_monitor_targets"
COOPERATIVE_STOP_GRACE_SECONDS = 1.5
COOPERATIVE_STOP_POLL_INTERVAL_SECONDS = 0.02
HARD_STOP_EXIT_TIMEOUT_SECONDS = 3.0
HARD_STOP_POLL_INTERVAL_SECONDS = 0.02


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    )


def _monitor_creation_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    )


def _force_terminate_process(pid: int) -> None:
    if pid <= 0:
        raise ValueError("supervisor PID must be positive")

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_TERMINATE = 0x0001
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        terminate_process = kernel32.TerminateProcess
        terminate_process.argtypes = [wintypes.HANDLE, wintypes.UINT]
        terminate_process.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        handle = open_process(PROCESS_TERMINATE, False, int(pid))
        if not handle:
            if not agent_control_module._process_is_running(pid):
                return
            error_code = ctypes.get_last_error()
            raise OSError(
                error_code,
                f"unable to open supervisor PID {pid} for termination",
            )
        try:
            if not terminate_process(handle, 1):
                if not agent_control_module._process_is_running(pid):
                    return
                error_code = ctypes.get_last_error()
                raise OSError(
                    error_code,
                    f"unable to terminate supervisor PID {pid}",
                )
        finally:
            close_handle(handle)
        return

    os.kill(int(pid), signal.SIGKILL)


def _wait_for_process_exit(
    pid: int,
    *,
    timeout_seconds: float = HARD_STOP_EXIT_TIMEOUT_SECONDS,
    poll_interval: float = HARD_STOP_POLL_INTERVAL_SECONDS,
) -> None:
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    while agent_control_module._process_is_running(pid):
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"supervisor PID {pid} remained alive after emergency termination"
            )
        if poll_interval:
            time.sleep(max(0.0, float(poll_interval)))


def _wait_for_cooperative_stop(
    pid: int,
    *,
    timeout_seconds: float = COOPERATIVE_STOP_GRACE_SECONDS,
    poll_interval: float = COOPERATIVE_STOP_POLL_INTERVAL_SECONDS,
) -> bool:
    """Return True when the supervisor exits inside the cooperative grace window."""
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    while agent_control_module._process_is_running(pid):
        if time.monotonic() >= deadline:
            return False
        if poll_interval:
            time.sleep(max(0.0, float(poll_interval)))
    return True


def _validated_hard_stop_status(
    control: BalatroAgentControl,
    pid: int,
) -> dict:
    status = control.read_status()
    if not status:
        return {}

    state = str(status.get("state") or "").upper()
    if state == "OFF":
        raise RuntimeError(
            "refusing emergency hard stop because control status says OFF while "
            f"agent.pid points at running PID {pid}"
        )

    status_pid = status.get("pid")
    if status_pid is None:
        return status
    try:
        normalized_status_pid = int(status_pid)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "refusing emergency hard stop because control status PID is invalid"
        ) from error
    if normalized_status_pid != pid:
        raise RuntimeError(
            "refusing emergency hard stop because control status PID does not "
            f"match agent.pid ({normalized_status_pid} != {pid})"
        )
    return status


def launch_monitor(control: BalatroAgentControl) -> None:
    command = [
        sys.executable,
        "-m",
        MONITOR_MODULE,
        "--control-dir",
        str(control.directory),
    ]
    subprocess.Popen(
        command,
        cwd=_repo_root(),
        stdin=subprocess.DEVNULL,
        close_fds=True,
        creationflags=_monitor_creation_flags(),
    )


def start_agent(
    control: BalatroAgentControl,
    *,
    session_id: str | None = None,
    unlock_jokers: tuple[str, ...] = (),
    collection_first: bool = False,
    launch_live_monitor: bool = True,
) -> int:
    running = control.running_pid()
    if running is not None:
        raise RuntimeError(f"Balatro agent is already ON as PID {running}")
    if not control.acquire_start_lock():
        raise RuntimeError("Balatro agent start is already in progress")

    control.clear_stop_request()
    command = [
        sys.executable,
        "-m",
        SUPERVISOR_MODULE,
        "--control-dir",
        str(control.directory),
    ]
    if session_id:
        command.extend(("--session-id", str(session_id)))
    for target in unlock_jokers:
        command.extend(("--unlock-joker", str(target)))
    if collection_first:
        command.append("--collection-first")

    control.ensure_directory()
    log_path = control.directory / "agent.log"
    control.write_status(
        "STARTING",
        pid=None,
        session_id=session_id,
        log_path=str(log_path),
    )
    try:
        log_handle = log_path.open("a", encoding="utf-8")
        try:
            process = subprocess.Popen(
                command,
                cwd=_repo_root(),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=_creation_flags(),
            )
        finally:
            log_handle.close()
        control.claim_current_process(process.pid)
        if launch_live_monitor:
            try:
                launch_monitor(control)
            except (OSError, subprocess.SubprocessError):
                pass
        return int(process.pid)
    except Exception:
        control.release_start_lock()
        control.clear_pid()
        control.write_status("OFF", reason="supervisor launch failed")
        raise


def hard_stop_agent(control: BalatroAgentControl) -> int | None:
    """Force-terminate only the recorded supervisor process.

    This is an emergency fallback for a supervisor that cannot reach the normal
    cooperative stop checkpoint. It never targets Balatro itself. An action that
    Balatro already consumed before the kill may still finish normally.
    """
    pid = control.running_pid()
    if pid is None:
        return None

    current = _validated_hard_stop_status(control, pid)
    metadata = {
        "pid": pid,
        "session_id": current.get("session_id"),
        "attempt": current.get("attempt"),
        "run_id": current.get("run_id"),
    }
    control.write_status(
        "HARD_STOPPING",
        **metadata,
        reason="emergency hard stop requested; force-terminating supervisor only",
    )
    try:
        _force_terminate_process(pid)
        _wait_for_process_exit(pid)
    finally:
        control.clear_pid()
        control.clear_stop_request()
        control.clear_start_lock()
        control.clear_telemetry()
        control.write_status(
            "OFF",
            **metadata,
            reason="emergency hard stop completed; supervisor force-terminated",
        )
    return pid


def stop_agent(control: BalatroAgentControl, *, hard: bool = False) -> int | None:
    if hard:
        return hard_stop_agent(control)

    pid = control.running_pid()
    if pid is None:
        control.clear_stop_request()
        control.clear_start_lock()
        control.clear_telemetry()
        control.write_status("OFF", reason="agent already stopped")
        return None

    control.request_stop()
    if _wait_for_cooperative_stop(pid):
        return pid

    # A cooperative stop may be delayed by a long policy calculation. Escalate only
    # the recorded supervisor PID; never terminate Balatro itself.
    return hard_stop_agent(control)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Toggle the persistent Balatro autonomous supervisor ON/OFF."
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--session-id")
    parser.add_argument("--unlock-joker", action="append", default=[])
    parser.add_argument("--collection-first", action="store_true")
    parser.add_argument("--hard-stop", action="store_true")
    parser.add_argument("--no-monitor", action="store_true")
    args = parser.parse_args()

    control = BalatroAgentControl(args.control_dir)
    pid = control.running_pid()
    if pid is not None:
        stopped = stop_agent(control, hard=bool(args.hard_stop))
        if args.hard_stop:
            print(f"Balatro agent HARD STOP complete (supervisor PID {stopped}).")
        else:
            print(f"Balatro agent stop requested (supervisor PID {stopped}).")
        return 0

    started = start_agent(
        control,
        session_id=args.session_id,
        unlock_jokers=tuple(args.unlock_joker),
        collection_first=bool(args.collection_first),
        launch_live_monitor=not args.no_monitor,
    )
    print(f"Balatro agent ON (supervisor PID {started}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())