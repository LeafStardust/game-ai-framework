from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .agent_control import BalatroAgentControl


SUPERVISOR_MODULE = "games.balatro.live.external.balatro_agent_supervisor"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    )


def start_agent(
    control: BalatroAgentControl,
    *,
    session_id: str | None = None,
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

    control.ensure_directory()
    log_path = control.directory / "agent.log"
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
        # Publish the child PID immediately so a second toggle cannot start a
        # duplicate supervisor during Python import/attachment startup.
        control.claim_current_process(process.pid)
        control.write_status(
            "STARTING",
            pid=process.pid,
            log_path=str(log_path),
        )
        return int(process.pid)
    except Exception:
        control.release_start_lock()
        control.clear_pid()
        raise


def stop_agent(control: BalatroAgentControl) -> int | None:
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
        reason="manual toggle OFF requested; stop before next gameplay action",
    )
    return pid


def toggle_agent(
    control: BalatroAgentControl,
    *,
    session_id: str | None = None,
) -> tuple[str, int | None]:
    running = control.running_pid()
    if running is not None:
        stop_agent(control)
        return "STOPPING", running
    return "STARTING", start_agent(control, session_id=session_id)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Toggle the Balatro autonomous supervisor. ON launches one detached "
            "supervisor process. OFF writes a cooperative stop request; it never "
            "kills Balatro or interrupts an already-submitted gameplay action."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--session-id")
    parser.add_argument("--status", action="store_true")
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

    try:
        state, pid = toggle_agent(control, session_id=args.session_id)
    except Exception as error:
        print("Balatro Agent toggle -> FAIL")
        print(f"Reason -> {error}")
        return 2

    if state == "STARTING":
        print("Balatro Agent is OFF.")
        print("Turning ON...")
        print(f"Supervisor PID -> {pid}")
        print("Playbook selection -> automatic from live deck/stake")
        print("Loss handling -> retry lifecycle enabled; native restart still fail-closed")
        print("Win handling -> automatic OFF")
        return 0

    print("Balatro Agent is ON.")
    print("Turning OFF...")
    print(f"Supervisor PID -> {pid}")
    print("Stop semantics -> before the next gameplay action")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
