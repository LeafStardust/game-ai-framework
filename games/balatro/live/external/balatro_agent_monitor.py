from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .agent_control import BalatroAgentControl


DEFAULT_REFRESH_SECONDS = 0.50
DEFAULT_FINAL_HOLD_SECONDS = 5.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _balatro_process_running() -> bool:
    if os.name != "nt":
        return True
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Balatro.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=2.0,
            creationflags=creationflags,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "balatro.exe" in (result.stdout or "").lower()


def _read_jsonl_tail(path: Path, *, limit: int = 80) -> list[dict[str, Any]]:
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    rows: list[dict[str, Any]] = []
    for raw in raw_lines[-max(1, int(limit)) :]:
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _latest(rows: list[dict[str, Any]], event_name: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row.get("event") == event_name:
            return row
    return None


def _action_text(action: Any) -> str:
    if not isinstance(action, dict):
        return "-"
    name = str(action.get("name") or "-")
    details: list[str] = []
    indices = action.get("indices")
    if isinstance(indices, list) and indices:
        details.append("indices=" + ",".join(str(item) for item in indices))
    target = action.get("target")
    if isinstance(target, dict):
        label = target.get("label") or target.get("name") or target.get("center")
        if label:
            details.append(str(label))
    return name + (" " + " ".join(details) if details else "")


def _last_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for name in ("action_result", "observation", "run_finished", "run_started"):
        row = _latest(rows, name)
        if not row:
            continue
        data = row.get("data")
        if not isinstance(data, dict):
            continue
        state = data.get("state")
        if isinstance(state, dict):
            return state
    return {}


def _safe(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def build_dashboard(
    status: dict[str, Any],
    *,
    supervisor_pid: int | None,
    balatro_running: bool,
    rows: list[dict[str, Any]],
) -> str:
    state = str(status.get("state") or "UNKNOWN")
    last_state = _last_state(rows)
    payload = last_state.get("payload") if isinstance(last_state.get("payload"), dict) else {}

    latest_decision = _latest(rows, "decision") or {}
    decision_data = latest_decision.get("data") if isinstance(latest_decision.get("data"), dict) else {}
    rationale = decision_data.get("rationale") if isinstance(decision_data.get("rationale"), dict) else {}
    notes = rationale.get("notes") if isinstance(rationale.get("notes"), list) else []

    latest_result = _latest(rows, "action_result") or {}
    result_data = latest_result.get("data") if isinstance(latest_result.get("data"), dict) else {}

    phase = last_state.get("phase") or status.get("phase") or "-"
    run_active = (
        supervisor_pid is not None
        and balatro_running
        and state in {"STARTING", "ON", "RESTARTING", "STOPPING"}
        and str(phase) != "GAME_OVER"
    )

    round_data = payload.get("round") if isinstance(payload.get("round"), dict) else {}
    blind = payload.get("blind") if isinstance(payload.get("blind"), dict) else {}

    score = payload.get("score")
    blind_score = blind.get("score")
    if score is not None and blind_score is not None:
        score_text = f"{score} / {blind_score}"
    else:
        score_text = _safe(score)

    lines = [
        "=" * 78,
        "BALATRO AGENT LIVE MONITOR",
        "=" * 78,
        f"Agent state      : {state}",
        f"Supervisor      : {'RUNNING' if supervisor_pid is not None else 'STOPPED'}"
        + (f" (PID {supervisor_pid})" if supervisor_pid is not None else ""),
        f"Balatro.exe     : {'RUNNING' if balatro_running else 'NOT RUNNING'}",
        f"Run ongoing     : {'YES' if run_active else 'NO'}",
        "",
        f"Session         : {_safe(status.get('session_id'))}",
        f"Attempt         : {_safe(status.get('attempt'))}",
        f"Run ID          : {_safe(status.get('run_id'))}",
        f"Deck / Stake    : {_safe(status.get('deck'))} / {_safe(status.get('stake'))}",
        f"Playbook        : {_safe(status.get('playbook'))} v{_safe(status.get('playbook_version'))}",
        f"Current phase   : {_safe(phase)}",
        f"Ante / Round    : {_safe(payload.get('ante_num'))} / {_safe(payload.get('round_num'))}",
        f"Score / Blind   : {score_text}",
        f"Hands / Discards: {_safe(round_data.get('hands_left'))} / {_safe(round_data.get('discards_left'))}",
        f"Money           : ${_safe(payload.get('money'))}",
        "",
        "LAST AGENT DECISION",
        "-" * 78,
        f"Action          : {_action_text(decision_data.get('action'))}",
        f"Decision source : {_safe(rationale.get('decision_source'))}",
    ]

    if notes:
        lines.append("Reasoning        :")
        for note in notes[:10]:
            lines.append(f"  - {note}")
    else:
        lines.append("Reasoning        : -")

    if latest_result:
        lines.extend(
            [
                "",
                "LAST EXECUTION RESULT",
                "-" * 78,
                f"Success         : {_safe(result_data.get('success'))}",
                f"Result action   : {_action_text(result_data.get('action'))}",
                f"Log event       : {_safe(latest_result.get('sequence'))}",
                f"Logged at UTC   : {_safe(latest_result.get('timestamp'))}",
            ]
        )

    reason = status.get("reason")
    if reason:
        lines.extend(["", f"Status reason    : {reason}"])

    lines.extend(
        [
            "",
            "This window is read-only. Close it at any time; the agent keeps running.",
            "Use BalatroAgentToggle.bat to stop the agent cooperatively.",
        ]
    )
    return "\n".join(lines)


def _run_log_rows(status: dict[str, Any], run_log_directory: Path) -> list[dict[str, Any]]:
    run_id = status.get("run_id")
    if not run_id:
        return []
    return _read_jsonl_tail(run_log_directory / f"{run_id}.jsonl")


def monitor(
    control: BalatroAgentControl,
    *,
    run_log_directory: Path,
    refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
    final_hold_seconds: float = DEFAULT_FINAL_HOLD_SECONDS,
) -> int:
    refresh_seconds = max(0.10, float(refresh_seconds))
    final_hold_seconds = max(0.0, float(final_hold_seconds))
    last_rendered: str | None = None
    off_since: float | None = None

    while True:
        status = control.read_status()
        pid = control.running_pid()
        balatro_running = _balatro_process_running()
        rows = _run_log_rows(status, run_log_directory)
        rendered = build_dashboard(
            status,
            supervisor_pid=pid,
            balatro_running=balatro_running,
            rows=rows,
        )

        if rendered != last_rendered:
            os.system("cls" if os.name == "nt" else "clear")
            print(rendered, flush=True)
            last_rendered = rendered

        if str(status.get("state") or "") == "OFF" and pid is None:
            if off_since is None:
                off_since = time.monotonic()
            elif time.monotonic() - off_since >= final_hold_seconds:
                return 0
        else:
            off_since = None

        time.sleep(refresh_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only live dashboard for the Balatro autonomous supervisor."
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    parser.add_argument("--refresh-seconds", type=float, default=DEFAULT_REFRESH_SECONDS)
    parser.add_argument("--final-hold-seconds", type=float, default=DEFAULT_FINAL_HOLD_SECONDS)
    args = parser.parse_args()

    run_log_directory = Path(args.run_log_directory)
    if not run_log_directory.is_absolute():
        run_log_directory = _repo_root() / run_log_directory

    return monitor(
        BalatroAgentControl(args.control_dir),
        run_log_directory=run_log_directory,
        refresh_seconds=args.refresh_seconds,
        final_hold_seconds=args.final_hold_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
