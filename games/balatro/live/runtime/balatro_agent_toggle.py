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
    if control.running_monitor_pid() is not None:
        return
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
    except Exception as error:
        control.write_status(
            "HARD_STOP_FAILED",
            **metadata,
            reason=f"emergency hard stop failed: {error}",
        )
        raise

    control.mark_off(
        reason="emergency hard stop; supervisor force-terminated; Balatro left running",
        session_id=current.get("session_id"),
        attempt=current.get("attempt"),
        run_id=current.get("run_id"),
    )
    return pid


def stop_agent(control: BalatroAgentControl) -> int | None:
    """Stop the supervisor with bounded cooperative shutdown and safe escalation."""
    pid = control.running_pid()
    if pid is None:
        return None

    control.request_stop()
    current = control.read_status()
    control.write_status(
        "STOPPING",
        pid=pid,
        session_id=current.get("session_id"),
        attempt=current.get("attempt"),
        run_id=current.get("run_id"),
        reason=(
            "manual toggle OFF requested; cooperative stop in progress; "
            "supervisor-only hard stop will follow if the grace window expires"
        ),
    )

    if _wait_for_cooperative_stop(pid):
        control.clear_pid(expected_pid=pid)
        return pid

    hard_stop_agent(control)
    return pid


def restart_agent(
    control: BalatroAgentControl,
    *,
    session_id: str | None = None,
    unlock_jokers: tuple[str, ...] = (),
    collection_first: bool = False,
) -> tuple[int | None, int]:
    """Restart the supervisor without opening another live-monitor window."""
    previous_pid = control.running_pid()
    if previous_pid is not None:
        stop_agent(control)

    new_pid = start_agent(
        control,
        session_id=session_id,
        unlock_jokers=unlock_jokers,
        collection_first=collection_first,
        launch_live_monitor=False,
    )
    return previous_pid, new_pid


def toggle_agent(
    control: BalatroAgentControl,
    *,
    session_id: str | None = None,
    unlock_jokers: tuple[str, ...] = (),
    collection_first: bool = False,
) -> tuple[str, int | None]:
    running = control.running_pid()
    if running is not None:
        stop_agent(control)
        return "OFF", running
    return "STARTING", start_agent(
        control,
        session_id=session_id,
        unlock_jokers=unlock_jokers,
        collection_first=collection_first,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Toggle or restart the Balatro autonomous supervisor. ON launches one "
            "detached supervisor process plus a read-only live monitor window. "
            "Normal OFF/restart requests a cooperative stop and automatically "
            "escalates to a validated supervisor-only hard stop if the grace window "
            "expires. --hard-stop forces that emergency path immediately."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--session-id")
    parser.add_argument(
        "--unlock-joker",
        action="append",
        choices=("auto", "hit_the_road", "stuntman"),
        default=[],
        help="enable a default-off Joker unlock campaign when turning the agent ON",
    )
    parser.add_argument(
        "--collection-first",
        action="store_true",
        help="prioritize permanent profile collection progress over winning the run",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--hard-stop", action="store_true")
    mode.add_argument(
        "--restart",
        action="store_true",
        help="restart the supervisor; if currently OFF, start it normally",
    )
    args = parser.parse_args()

    control = BalatroAgentControl(args.control_dir)
    if args.status:
        pid = control.running_pid()
        status = control.read_status()
        print(f"Balatro Agent -> {'ON' if pid is not None else 'OFF'}")
        if pid is not None:
            print(f"PID -> {pid}")
        if status:
            print(f"State -> {status.get('state', 'UNKNOWN')}")
            if status.get("session_id"):
                print(f"Session -> {status['session_id']}")
            if status.get("attempt") is not None:
                print(f"Attempt -> {status['attempt']}")
            if status.get("deck") and status.get("stake"):
                print(f"Run -> {status['deck']} / {status['stake']}")
            if status.get("playbook"):
                print(
                    "Playbook -> "
                    f"{status['playbook']} v{status.get('playbook_version', '?')}"
                )
            if status.get("reason"):
                print(f"Reason -> {status['reason']}")
        return 0

    if args.hard_stop:
        try:
            pid = hard_stop_agent(control)
        except Exception as error:
            print("Balatro Agent emergency hard stop -> FAIL")
            print(f"Reason -> {error}")
            return 2
        if pid is None:
            print("Balatro Agent -> OFF")
            print("Emergency hard stop -> no running supervisor")
            return 0
        print("Balatro Agent -> OFF")
        print(f"Supervisor PID -> {pid}")
        print("Emergency hard stop -> supervisor force-terminated")
        print("Balatro process -> untouched")
        print("Already-consumed gameplay action -> may still finish")
        return 0

    if args.restart:
        try:
            previous_pid, new_pid = restart_agent(
                control,
                session_id=args.session_id,
                unlock_jokers=tuple(args.unlock_joker),
                collection_first=args.collection_first,
            )
        except Exception as error:
            print("Balatro Agent restart -> FAIL")
            print(f"Reason -> {error}")
            return 2

        if previous_pid is None:
            print("Balatro Agent was OFF.")
            print("Starting...")
        else:
            print("Balatro Agent was ON.")
            print(f"Previous supervisor PID -> {previous_pid}")
            print("Restarting...")
        print(f"New supervisor PID -> {new_pid}")
        print("Balatro Agent -> ON")
        print("Balatro process -> untouched")
        print("Live monitor -> unchanged; no new window opened")
        return 0

    try:
        state, pid = toggle_agent(
            control,
            session_id=args.session_id,
            unlock_jokers=tuple(args.unlock_joker),
            collection_first=args.collection_first,
        )
    except Exception as error:
        print("Balatro Agent toggle -> FAIL")
        print(f"Reason -> {error}")
        return 2

    if state == "STARTING":
        print("Balatro Agent is OFF.")
        print("Turning ON...")
        print(f"Supervisor PID -> {pid}")
        print("Live monitor -> opening in a separate terminal window")
        print("Playbook selection -> automatic from live deck/stake")
        if args.unlock_joker:
            print("Unlock campaign -> " + ", ".join(args.unlock_joker))
        else:
            print("Unlock campaign -> OFF")
        print(
            "Collection-first mode -> "
            + ("ON" if args.collection_first else "OFF")
        )
        print("Loss handling -> automatic fresh same-deck/stake native retry")
        print("Win handling -> automatic OFF")
        print("Crash reporting -> automatic traceback + report file")
        return 0

    print("Balatro Agent was ON.")
    print("Turning OFF...")
    print(f"Supervisor PID -> {pid}")
    print("Balatro Agent -> OFF")
    print(
        "Stop semantics -> cooperative first; automatic supervisor-only hard stop "
        f"after {COOPERATIVE_STOP_GRACE_SECONDS:.1f}s if still running"
    )
    print("Balatro process -> untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
