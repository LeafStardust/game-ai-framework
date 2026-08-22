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


def _modeled_clear_probability(rationale: dict[str, Any]) -> tuple[float | None, float | None]:
    postmortem = rationale.get("postmortem")
    if not isinstance(postmortem, dict) or postmortem.get("layer") != "D1":
        return None, None
    selected = postmortem.get("selected")
    selected_probability = None
    if isinstance(selected, dict):
        value = selected.get("clear_probability")
        if isinstance(value, (int, float)):
            selected_probability = float(value)
    attempts = postmortem.get("search_attempts")
    if isinstance(attempts, list):
        for attempt in reversed(attempts):
            if not isinstance(attempt, dict):
                continue
            value = attempt.get("best_clear_probability")
            if isinstance(value, (int, float)):
                return float(value), selected_probability
    return selected_probability, selected_probability


def _strategy_display_name(strategy_id: str) -> str:
    return str(strategy_id).replace("_", " ").title()


def _strategy_dashboard_fields(rationale: dict[str, Any]) -> dict[str, str]:
    empty = {"strategy": "-", "status": "-", "score": "-", "pressure": "-", "relevant": "-", "path": "-"}
    postmortem = rationale.get("postmortem")
    if not isinstance(postmortem, dict):
        return empty
    strategy = postmortem.get("strategy")
    if not isinstance(strategy, dict):
        return empty
    ranked = strategy.get("ranked")
    ranked_rows = ranked if isinstance(ranked, list) else []
    assessment_by_id = {str(row.get("strategy_id")): row for row in ranked_rows if isinstance(row, dict) and row.get("strategy_id")}
    dominant_id = strategy.get("dominant_strategy_id")
    if dominant_id is None:
        dominant_name = "NONE (ordinary/meta value leads)"
        dominant = None
    else:
        dominant_id = str(dominant_id)
        dominant = assessment_by_id.get(dominant_id)
        dominant_name = str(dominant.get("name")) if dominant is not None and dominant.get("name") else _strategy_display_name(dominant_id)
    relevant_ids = strategy.get("relevant_strategy_ids")
    relevant_names: list[str] = []
    if isinstance(relevant_ids, list):
        for raw_id in relevant_ids:
            strategy_id = str(raw_id)
            row = assessment_by_id.get(strategy_id)
            relevant_names.append(str(row.get("name")) if row is not None and row.get("name") else _strategy_display_name(strategy_id))
    path_names: list[str] = []
    nodes = strategy.get("nodes")
    if dominant_id is not None and isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict) or str(node.get("strategy_id")) != dominant_id:
                continue
            raw_path = node.get("path")
            if isinstance(raw_path, list):
                for raw_id in raw_path:
                    strategy_id = str(raw_id)
                    row = assessment_by_id.get(strategy_id)
                    if strategy_id == dominant_id:
                        path_names.append(dominant_name)
                    elif row is not None and row.get("name"):
                        path_names.append(str(row.get("name")))
                    else:
                        path_names.append(_strategy_display_name(strategy_id))
            break
    score = dominant.get("score") if dominant is not None else None
    pressure = strategy.get("strategy_pressure")
    return {
        "strategy": dominant_name,
        "status": _safe(strategy.get("active_status")),
        "score": f"{float(score):.3f}" if isinstance(score, (int, float)) else "-",
        "pressure": f"{float(pressure):.3f}" if isinstance(pressure, (int, float)) else "-",
        "relevant": ", ".join(relevant_names) if relevant_names else "NONE",
        "path": " -> ".join(path_names) if path_names else "-",
    }


def _find_health_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        required = {"survival", "immediate", "scaling", "coherence", "runway"}
        if required.issubset(value):
            return value
        for key in ("build_health", "health", "realized_strength"):
            child = value.get(key)
            found = _find_health_dict(child)
            if found is not None:
                return found
        for child in value.values():
            if isinstance(child, (dict, list, tuple)):
                found = _find_health_dict(child)
                if found is not None:
                    return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _find_health_dict(child)
            if found is not None:
                return found
    return None


def _find_named(value: Any, names: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for name in names:
            if name in value:
                return value[name]
        for child in value.values():
            if isinstance(child, (dict, list, tuple)):
                found = _find_named(child, names)
                if found is not None:
                    return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _find_named(child, names)
            if found is not None:
                return found
    return None


def _pct_text(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1f}%"
    return _safe(value)


def _engine_text(raw: Any) -> str:
    if not isinstance(raw, (list, tuple)) or not raw:
        return "NONE"
    parts: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            engine_id = item.get("engine_id") or item.get("id") or item.get("name") or "engine"
            state = item.get("state") or item.get("status") or "-"
            parts.append(f"{engine_id}={state}")
        else:
            parts.append(str(item))
    return ", ".join(parts)


def _roles_text(raw: Any) -> str:
    if isinstance(raw, dict):
        parts: list[str] = []
        for key, value in raw.items():
            if isinstance(value, (list, tuple, set)):
                label = ",".join(str(v) for v in value)
                parts.append(f"{key}=[{label}]")
            else:
                parts.append(f"{key}={value}")
        return "; ".join(parts) if parts else "NONE"
    if isinstance(raw, (list, tuple)):
        parts = []
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name") or item.get("joker") or item.get("component") or item.get("id") or "component"
                role = item.get("role") or item.get("state") or "-"
                parts.append(f"{name}={role}")
            else:
                parts.append(str(item))
        return ", ".join(parts) if parts else "NONE"
    return _safe(raw, "NONE")


def _health_dashboard_fields(rationale: dict[str, Any]) -> dict[str, Any]:
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else rationale
    health = _find_health_dict(postmortem)
    if health is None:
        return {"available": False, "total": "-", "survival": "-", "immediate": "-", "scaling": "-", "coherence": "-", "runway": "-", "critical": "-", "scaling_deficit": "-", "engines": "NONE", "roles": "NONE", "warnings": []}
    warnings = health.get("warnings")
    if not isinstance(warnings, list):
        warnings = list(warnings) if isinstance(warnings, tuple) else []
    extra_warnings = _find_named(postmortem, ("inactive_engine_warnings", "build_health_warnings"))
    if isinstance(extra_warnings, (list, tuple)):
        for warning in extra_warnings:
            if str(warning) not in {str(item) for item in warnings}:
                warnings.append(warning)
    engines = health.get("engines")
    if engines is None:
        engines = _find_named(postmortem, ("realized_engines", "engine_states", "engines"))
    roles = _find_named(postmortem, ("component_roles", "joker_roles", "realized_component_roles"))
    return {
        "available": True,
        "total": _pct_text(health.get("total")),
        "survival": _pct_text(health.get("survival")),
        "immediate": _pct_text(health.get("immediate")),
        "scaling": _pct_text(health.get("scaling")),
        "coherence": _pct_text(health.get("coherence")),
        "runway": _pct_text(health.get("runway")),
        "critical": _safe(health.get("critical")),
        "scaling_deficit": _safe(health.get("scaling_deficit")),
        "engines": _engine_text(engines),
        "roles": _roles_text(roles),
        "warnings": [str(item) for item in warnings],
    }


def build_dashboard(status: dict[str, Any], *, supervisor_pid: int | None, balatro_running: bool, rows: list[dict[str, Any]], telemetry: dict[str, Any] | None = None) -> str:
    telemetry = telemetry or {}
    state = str(status.get("state") or "UNKNOWN")
    last_state = _last_state(rows)
    payload = last_state.get("payload") if isinstance(last_state.get("payload"), dict) else {}
    latest_decision = _latest(rows, "decision") or {}
    decision_data = latest_decision.get("data") if isinstance(latest_decision.get("data"), dict) else {}
    rationale = decision_data.get("rationale") if isinstance(decision_data.get("rationale"), dict) else {}
    notes = list(rationale.get("notes")) if isinstance(rationale.get("notes"), list) else []
    strategy_fields = _strategy_dashboard_fields(rationale)
    health_fields = _health_dashboard_fields(rationale)
    modeled_clear_probability, selected_plan_probability = _modeled_clear_probability(rationale)
    if modeled_clear_probability is not None:
        replacement = f"clear_probability={modeled_clear_probability:.6f}"
        replaced = False
        for index, note in enumerate(notes):
            if str(note).startswith("clear_probability="):
                notes[index] = replacement
                replaced = True
                break
        if not replaced:
            notes.insert(0, replacement)
        if selected_plan_probability is not None and abs(selected_plan_probability - modeled_clear_probability) > 1e-12:
            notes.append("selected_plan_clear_probability=" f"{selected_plan_probability:.6f} (depth-1/fallback diagnostic)")
    latest_result = _latest(rows, "action_result") or {}
    result_data = latest_result.get("data") if isinstance(latest_result.get("data"), dict) else {}
    phase = telemetry.get("phase") or last_state.get("phase") or status.get("phase") or "-"
    run_active = supervisor_pid is not None and balatro_running and state in {"STARTING", "ON", "RESTARTING", "STOPPING"} and str(phase) != "GAME_OVER"
    round_data = payload.get("round") if isinstance(payload.get("round"), dict) else {}
    blind = payload.get("blind") if isinstance(payload.get("blind"), dict) else {}
    score = payload.get("score")
    blind_score = blind.get("score")
    score_text = f"{score} / {blind_score}" if score is not None and blind_score is not None else _safe(score)
    activity_notes = telemetry.get("notes") if isinstance(telemetry.get("notes"), list) else []
    lines = [
        "=" * 78, "BALATRO AGENT LIVE MONITOR", "=" * 78,
        f"Agent state      : {state}",
        f"Agent activity   : {_safe(telemetry.get('activity'), 'WAITING')}",
        f"Supervisor      : {'RUNNING' if supervisor_pid is not None else 'STOPPED'}" + (f" (PID {supervisor_pid})" if supervisor_pid is not None else ""),
        f"Balatro.exe     : {'RUNNING' if balatro_running else 'NOT RUNNING'}",
        f"Run ongoing     : {'YES' if run_active else 'NO'}", "",
        f"Session         : {_safe(status.get('session_id') or telemetry.get('session_id'))}",
        f"Attempt         : {_safe(status.get('attempt') if status.get('attempt') is not None else telemetry.get('attempt'))}",
        f"Run ID          : {_safe(status.get('run_id') or telemetry.get('run_id'))}",
        f"Deck / Stake    : {_safe(status.get('deck') or telemetry.get('deck'))} / {_safe(status.get('stake') or telemetry.get('stake'))}",
        f"Playbook        : {_safe(status.get('playbook'))} v{_safe(status.get('playbook_version'))}",
        f"Current phase   : {_safe(phase)}",
        f"Ante / Round    : {_safe(payload.get('ante_num'))} / {_safe(payload.get('round_num'))}",
        f"Score / Blind   : {score_text}",
        f"Hands / Discards: {_safe(round_data.get('hands_left'))} / {_safe(round_data.get('discards_left'))}",
        f"Money           : ${_safe(payload.get('money'))}", "",
        "CURRENT STRATEGY", "-" * 78,
        f"Strategy        : {strategy_fields['strategy']}",
        f"Status          : {strategy_fields['status']}",
        f"Score           : {strategy_fields['score']}",
        f"Pressure        : {strategy_fields['pressure']}",
        f"Relevant        : {strategy_fields['relevant']}",
        f"Path            : {strategy_fields['path']}", "",
        "BUILD HEALTH / REALIZED STRENGTH", "-" * 78,
        f"Health total    : {health_fields['total']}",
        f"Survival        : {health_fields['survival']}",
        f"Immediate       : {health_fields['immediate']}",
        f"Scaling         : {health_fields['scaling']}",
        f"Coherence       : {health_fields['coherence']}",
        f"Runway          : {health_fields['runway']}",
        f"Critical        : {health_fields['critical']}",
        f"Scaling deficit : {health_fields['scaling_deficit']}",
        f"Engines         : {health_fields['engines']}",
        f"Component roles : {health_fields['roles']}",
    ]
    if health_fields["warnings"]:
        lines.append("Warnings         :")
        for warning in health_fields["warnings"][:8]:
            lines.append(f"  - {warning}")
    else:
        lines.append("Warnings         : NONE" if health_fields["available"] else "Warnings         : -")
    lines.extend(["", "CURRENT AGENT ACTIVITY", "-" * 78,
        f"Activity        : {_safe(telemetry.get('activity'), 'WAITING')}",
        f"Action          : {_safe(telemetry.get('action'))}",
        f"Decision source : {_safe(telemetry.get('decision_source'))}",
        f"Detail          : {_safe(telemetry.get('detail'))}"])
    if activity_notes:
        lines.append("Current rationale:")
        for note in activity_notes[:10]:
            lines.append(f"  - {note}")
    lines.extend(["", "LAST LOGGED DECISION", "-" * 78,
        f"Action          : {_action_text(decision_data.get('action'))}",
        f"Decision source : {_safe(rationale.get('decision_source'))}"])
    if notes:
        lines.append("Reasoning        :")
        for note in notes[:10]:
            lines.append(f"  - {note}")
    else:
        lines.append("Reasoning        : -")
    if latest_result:
        lines.extend(["", "LAST EXECUTION RESULT", "-" * 78,
            f"Success         : {_safe(result_data.get('success'))}",
            f"Result action   : {_action_text(result_data.get('action'))}",
            f"Log event       : {_safe(latest_result.get('sequence'))}",
            f"Logged at UTC   : {_safe(latest_result.get('timestamp'))}"])
    reason = status.get("reason") or telemetry.get("reason")
    if reason:
        lines.extend(["", f"Status reason    : {reason}"])
    lines.extend(["", "This window is read-only. Close it at any time; the agent keeps running.", "Use BalatroAgentToggle.bat to stop the agent cooperatively."])
    return "\n".join(lines)


def _run_log_rows(status: dict[str, Any], run_log_directory: Path) -> list[dict[str, Any]]:
    run_id = status.get("run_id")
    if not run_id:
        return []
    return _read_jsonl_tail(run_log_directory / f"{run_id}.jsonl")


def monitor(control: BalatroAgentControl, *, run_log_directory: Path, refresh_seconds: float = DEFAULT_REFRESH_SECONDS, final_hold_seconds: float = DEFAULT_FINAL_HOLD_SECONDS) -> int:
    refresh_seconds = max(0.10, float(refresh_seconds))
    final_hold_seconds = max(0.0, float(final_hold_seconds))
    last_rendered: str | None = None
    off_since: float | None = None
    while True:
        status = control.read_status()
        telemetry = control.read_telemetry()
        pid = control.running_pid()
        balatro_running = _balatro_process_running()
        rows = _run_log_rows(status, run_log_directory)
        rendered = build_dashboard(status, supervisor_pid=pid, balatro_running=balatro_running, rows=rows, telemetry=telemetry)
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
    parser = argparse.ArgumentParser(description="Read-only live dashboard for the Balatro autonomous supervisor.")
    parser.add_argument("--control-dir")
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    parser.add_argument("--refresh-seconds", type=float, default=DEFAULT_REFRESH_SECONDS)
    parser.add_argument("--final-hold-seconds", type=float, default=DEFAULT_FINAL_HOLD_SECONDS)
    args = parser.parse_args()
    run_log_directory = Path(args.run_log_directory)
    if not run_log_directory.is_absolute():
        run_log_directory = _repo_root() / run_log_directory
    return monitor(BalatroAgentControl(args.control_dir), run_log_directory=run_log_directory, refresh_seconds=args.refresh_seconds, final_hold_seconds=args.final_hold_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
