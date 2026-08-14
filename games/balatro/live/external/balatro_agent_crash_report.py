from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from games.balatro.live.injected.bridge import default_bridge_dir

from .agent_control import BalatroAgentControl, _process_is_running
from .live_memory_observer import LiveMemoryBalatroObserver


DEFAULT_AGENT_LOG_LINES = 100
DEFAULT_RUN_LOG_LINES = 30


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_text(path: Path, *, max_chars: int = 20000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"<unavailable: {error}>"
    if len(text) <= max_chars:
        return text
    return "<truncated>\n" + text[-max_chars:]


def _tail(path: Path, lines: int) -> str:
    text = _read_text(path, max_chars=200000)
    if text.startswith("<unavailable:"):
        return text
    rows = text.splitlines()
    return "\n".join(rows[-max(1, int(lines)):])


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception as error:
        return f"<unavailable: {error}>"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return f"<unavailable: {detail or f'git exited {result.returncode}'}>"
    return result.stdout.strip() or "<empty>"


def _snapshot_section() -> str:
    try:
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
    except Exception as error:
        return f"Live snapshot -> unavailable ({type(error).__name__}: {error})"

    payload = snapshot.payload
    public = {
        "sequence": snapshot.sequence,
        "phase": snapshot.phase,
        "state_complete": snapshot.state_complete,
        "deck": payload.get("deck"),
        "stake": payload.get("stake"),
        "won": payload.get("won"),
        "ante_num": payload.get("ante_num"),
        "round_num": payload.get("round_num"),
        "score": payload.get("score"),
        "money": payload.get("money"),
        "blind": payload.get("blind"),
        "round": payload.get("round"),
        "live_state_source": payload.get("live_state_source"),
        "hidden_rng_exposed": payload.get("hidden_rng_exposed"),
        "hidden_draw_order_exposed": payload.get("hidden_draw_order_exposed"),
    }
    return _json_text(public)


def _bridge_files_section() -> str:
    directory = default_bridge_dir()
    command = directory / "command.txt"
    response = directory / "response.txt"
    rows = [
        f"Bridge directory -> {directory}",
        f"command.txt exists -> {command.exists()}",
        f"response.txt exists -> {response.exists()}",
        "Active bridge probe sent -> False",
        "Reason -> crash reporting is read-only and never creates a new bridge command",
    ]
    if command.exists():
        rows.append("command.txt contents:")
        rows.append(_read_text(command, max_chars=4000))
    if response.exists():
        rows.append("response.txt contents:")
        rows.append(_read_text(response, max_chars=4000))
    return "\n".join(rows)


def _session_section(status: dict[str, Any]) -> str:
    root = _repo_root()
    session_id = str(status.get("session_id") or "").strip()
    run_id = str(status.get("run_id") or "").strip()
    rows: list[str] = []

    if session_id:
        summary = root / "logs" / "balatro" / "sessions" / f"{session_id}.summary.json"
        rows.append(f"Session summary -> {summary}")
        rows.append(_read_text(summary, max_chars=40000))
    else:
        rows.append("Session summary -> no session_id in agent status")

    if run_id:
        run_log = root / "logs" / "balatro" / "runs" / f"{run_id}.jsonl"
        run_summary = root / "logs" / "balatro" / "runs" / f"{run_id}.summary.json"
        rows.append(f"Current attempt log -> {run_log}")
        rows.append(_tail(run_log, DEFAULT_RUN_LOG_LINES))
        rows.append(f"Current attempt summary -> {run_summary}")
        rows.append(_read_text(run_summary, max_chars=40000))
    else:
        rows.append("Current attempt log -> no run_id in agent status")

    return "\n".join(rows)


def _windows_events_section() -> str:
    if os.name != "nt":
        return "Windows Application events -> not applicable on this platform"

    script = r"""
$cutoff = (Get-Date).AddMinutes(-30)
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$cutoff} -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match 'Balatro\.exe|Balatro' } |
  Select-Object -First 8 TimeCreated, Id, ProviderName, LevelDisplayName, Message |
  Format-List |
  Out-String -Width 220
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as error:
        return f"Windows Application events -> unavailable ({error})"

    text = (result.stdout or "").strip()
    if not text:
        detail = (result.stderr or "").strip()
        return "Windows Application events -> none found in last 30 minutes" + (
            f" ({detail})" if detail else ""
        )
    return text


def build_crash_report(
    control: BalatroAgentControl | None = None,
    *,
    agent_log_lines: int = DEFAULT_AGENT_LOG_LINES,
    include_windows_events: bool = True,
    exception_text: str | None = None,
) -> str:
    control = control or BalatroAgentControl()
    status = control.read_status()
    recorded_pid = control.read_pid()
    pid_running = (
        _process_is_running(recorded_pid) if recorded_pid is not None else False
    )
    agent_log = control.directory / "agent.log"

    sections = [
        "=== BALATRO AGENT CRASH REPORT ===",
        f"Generated at UTC -> {_utc_now()}",
        f"Repository -> {_repo_root()}",
        f"Git branch -> {_git_value('branch', '--show-current')}",
        f"Git commit -> {_git_value('rev-parse', 'HEAD')}",
        "",
        "=== SUPERVISOR STATUS ===",
        f"Control directory -> {control.directory}",
        f"Recorded supervisor PID -> {recorded_pid}",
        f"Recorded PID still running -> {pid_running}",
        _json_text(status) if status else "<no valid status.json>",
        "",
        "=== LIVE BALATRO SNAPSHOT ===",
        _snapshot_section(),
        "",
        "=== BRIDGE FILE STATE ===",
        _bridge_files_section(),
        "",
        "=== CURRENT SESSION / ATTEMPT ===",
        _session_section(status),
        "",
        f"=== AGENT LOG TAIL ({max(1, int(agent_log_lines))} lines) ===",
        _tail(agent_log, max(1, int(agent_log_lines))),
    ]

    if exception_text:
        sections.extend(("", "=== PYTHON EXCEPTION ===", str(exception_text).rstrip()))

    if include_windows_events:
        sections.extend(("", "=== WINDOWS APPLICATION EVENTS (last 30 min) ===", _windows_events_section()))

    sections.extend(("", "=== END REPORT ==="))
    return "\n".join(sections) + "\n"


def write_crash_report(
    control: BalatroAgentControl | None = None,
    *,
    agent_log_lines: int = DEFAULT_AGENT_LOG_LINES,
    include_windows_events: bool = True,
    exception_text: str | None = None,
    output_path: str | Path | None = None,
) -> tuple[Path, str]:
    control = control or BalatroAgentControl()
    report = build_crash_report(
        control,
        agent_log_lines=agent_log_lines,
        include_windows_events=include_windows_events,
        exception_text=exception_text,
    )
    if output_path is None:
        directory = control.directory / "crash-reports"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"balatro-agent-crash-{_stamp()}.txt"
    else:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path, report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a paste-ready Balatro agent crash report. The report is read-only: "
            "it never sends a bridge/gameplay command."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--lines", type=int, default=DEFAULT_AGENT_LOG_LINES)
    parser.add_argument("--output")
    parser.add_argument("--no-windows-events", action="store_true")
    args = parser.parse_args()

    if args.lines < 1:
        parser.error("--lines must be positive")

    control = BalatroAgentControl(args.control_dir)
    try:
        path, report = write_crash_report(
            control,
            agent_log_lines=args.lines,
            include_windows_events=not args.no_windows_events,
            output_path=args.output,
        )
    except Exception as error:
        print("Balatro Agent crash report -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        return 2

    print(report, end="")
    print(f"Crash report saved -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
