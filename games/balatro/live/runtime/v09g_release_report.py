from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SESSION_SCHEMA = "balatro-agent-session-summary-v1"
RUN_SCHEMA = "balatro-run-experience-v1"
RUN_SUMMARY_SCHEMA = "balatro-run-summary-v1"
DIAGNOSTIC_SCHEMA = "balatro-diagnostic-v1"


@dataclass(frozen=True)
class ReleaseReport:
    session_id: str
    integrity_errors: tuple[str, ...]
    warnings: tuple[str, ...]
    phases: tuple[str, ...]
    actions: tuple[str, ...]
    pack_decisions: int
    targeted_pack_decisions: int
    loss_count: int
    attempt_count: int
    manual_stop: bool
    terminal_attempts: int
    diagnostic_events: int

    @property
    def integrity_ok(self) -> bool:
        return not self.integrity_errors


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_directory(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else _repo_root() / path


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(value)
    return rows


def _latest_session_summary(session_directory: Path) -> Path:
    candidates = tuple(session_directory.glob("*.summary.json"))
    if not candidates:
        raise FileNotFoundError(
            f"no Balatro session summaries found in {session_directory}"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _session_summary_path(
    session_directory: Path,
    session_id: str | None,
) -> Path:
    if session_id is None:
        return _latest_session_summary(session_directory)
    return session_directory / f"{session_id}.summary.json"


def _decision_notes(row: dict[str, Any]) -> tuple[str, ...]:
    data = row.get("data")
    if not isinstance(data, dict):
        return ()
    rationale = data.get("rationale")
    if not isinstance(rationale, dict):
        return ()
    notes = rationale.get("notes")
    if not isinstance(notes, list):
        return ()
    return tuple(str(note) for note in notes)


def _decision_source(row: dict[str, Any]) -> str:
    data = row.get("data")
    if not isinstance(data, dict):
        return ""
    rationale = data.get("rationale")
    if not isinstance(rationale, dict):
        return ""
    return str(rationale.get("decision_source") or "")


def _action_name(row: dict[str, Any]) -> str:
    data = row.get("data")
    if not isinstance(data, dict):
        return ""
    action = data.get("action")
    if not isinstance(action, dict):
        return ""
    return str(action.get("name") or "")


def _state_phase(row: dict[str, Any]) -> str | None:
    data = row.get("data")
    if not isinstance(data, dict):
        return None
    state = data.get("state")
    if not isinstance(state, dict):
        return None
    phase = state.get("phase")
    return str(phase) if phase else None


def _looks_targeted_pack_decision(row: dict[str, Any]) -> bool:
    if _decision_source(row) != "pack policy":
        return False
    notes = " ".join(_decision_notes(row)).lower()
    return any(
        token in notes
        for token in (
            "target_indices=",
            "target index",
            "target_indices",
            "targeted",
            "target gain",
        )
    )


def build_release_report(
    *,
    session_id: str | None = None,
    session_directory: str | Path = "logs/balatro/sessions",
    run_log_directory: str | Path = "logs/balatro/runs",
    diagnostic_directory: str | Path = "logs/balatro/diagnostics",
) -> ReleaseReport:
    sessions = _resolve_directory(session_directory)
    runs = _resolve_directory(run_log_directory)
    diagnostics = _resolve_directory(diagnostic_directory)
    summary_path = _session_summary_path(sessions, session_id)
    summary = _load_json(summary_path)

    errors: list[str] = []
    warnings: list[str] = []
    phases: set[str] = set()
    actions: set[str] = set()
    pack_decisions = 0
    targeted_pack_decisions = 0

    if summary.get("schema") != SESSION_SCHEMA:
        errors.append(f"unexpected session schema: {summary.get('schema')!r}")
    actual_session_id = str(summary.get("session_id") or "")
    if not actual_session_id:
        errors.append("session summary is missing session_id")
        actual_session_id = summary_path.name.removesuffix(".summary.json")

    attempts = summary.get("attempts")
    if not isinstance(attempts, list):
        errors.append("session summary attempts is not a list")
        attempts = []

    declared_attempt_count = summary.get("attempt_count")
    if declared_attempt_count != len(attempts):
        errors.append(
            "session attempt_count mismatch: "
            f"declared {declared_attempt_count!r}, observed {len(attempts)}"
        )

    terminal_attempts = 0
    for attempt in attempts:
        if not isinstance(attempt, dict):
            errors.append("session contains a non-object attempt")
            continue
        run_id = str(attempt.get("run_id") or "")
        if not run_id:
            errors.append("attempt missing run_id")
            continue

        outcome = str(attempt.get("outcome") or "")
        if outcome in {"WIN", "LOSS"}:
            terminal_attempts += 1

        run_path = runs / f"{run_id}.jsonl"
        run_summary_path = runs / f"{run_id}.summary.json"
        if not run_path.exists():
            errors.append(f"missing run log: {run_path}")
            continue
        if not run_summary_path.exists():
            errors.append(f"missing run summary: {run_summary_path}")

        try:
            rows = _load_jsonl(run_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"unable to read {run_path}: {error}")
            continue
        if not rows:
            errors.append(f"empty run log: {run_path}")
            continue

        expected_sequences = list(range(1, len(rows) + 1))
        observed_sequences = [row.get("sequence") for row in rows]
        if observed_sequences != expected_sequences:
            errors.append(f"non-contiguous run sequence: {run_id}")

        finished_rows = []
        action_results = 0
        for row in rows:
            if row.get("schema") != RUN_SCHEMA:
                errors.append(f"unexpected run schema in {run_id}")
                break
            if str(row.get("run_id") or "") != run_id:
                errors.append(f"run identity mismatch in {run_id}")
                break
            event = str(row.get("event") or "")
            if event == "run_finished":
                finished_rows.append(row)
            if event == "decision":
                action_name = _action_name(row)
                if action_name:
                    actions.add(action_name)
                if _decision_source(row) == "pack policy":
                    pack_decisions += 1
                    if _looks_targeted_pack_decision(row):
                        targeted_pack_decisions += 1
            if event == "action_result":
                action_results += 1
                data = row.get("data")
                if not isinstance(data, dict) or data.get("success") is not True:
                    errors.append(
                        f"experience log contains unsuccessful action_result: {run_id}"
                    )
            phase = _state_phase(row)
            if phase:
                phases.add(phase)

        if len(finished_rows) != 1:
            errors.append(
                f"run {run_id} must contain exactly one run_finished event; "
                f"observed {len(finished_rows)}"
            )

        declared_actions = attempt.get("actions")
        if isinstance(declared_actions, int) and action_results != declared_actions:
            errors.append(
                f"run {run_id} action count mismatch: "
                f"session={declared_actions}, logged={action_results}"
            )

        if run_summary_path.exists():
            try:
                run_summary = _load_json(run_summary_path)
            except (OSError, json.JSONDecodeError, ValueError) as error:
                errors.append(f"unable to read {run_summary_path}: {error}")
            else:
                if run_summary.get("schema") != RUN_SUMMARY_SCHEMA:
                    errors.append(f"unexpected run-summary schema: {run_id}")
                if run_summary.get("event_count") != len(rows):
                    errors.append(f"run-summary event_count mismatch: {run_id}")
                if run_summary.get("last_sequence") != rows[-1].get("sequence"):
                    errors.append(f"run-summary last_sequence mismatch: {run_id}")

    diagnostic_events = 0
    diagnostic_path = diagnostics / f"{actual_session_id}.jsonl"
    if diagnostic_path.exists():
        try:
            diagnostic_rows = _load_jsonl(diagnostic_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"unable to read {diagnostic_path}: {error}")
        else:
            diagnostic_events = len(diagnostic_rows)
            expected = list(range(1, diagnostic_events + 1))
            observed = [row.get("sequence") for row in diagnostic_rows]
            if observed != expected:
                errors.append("diagnostic sequence is not contiguous")
            if any(row.get("schema") != DIAGNOSTIC_SCHEMA for row in diagnostic_rows):
                errors.append("unexpected diagnostic schema")
            if any(
                str(row.get("session_id") or "") != actual_session_id
                for row in diagnostic_rows
            ):
                errors.append("diagnostic session identity mismatch")
            if diagnostic_events:
                warnings.append(
                    f"session contains {diagnostic_events} diagnostic failure/block event(s)"
                )

    loss_count = int(summary.get("loss_count") or 0)
    manual_stop = str(summary.get("stop_reason") or "") == "manual stop requested"

    return ReleaseReport(
        session_id=actual_session_id,
        integrity_errors=tuple(errors),
        warnings=tuple(warnings),
        phases=tuple(sorted(phases)),
        actions=tuple(sorted(actions)),
        pack_decisions=pack_decisions,
        targeted_pack_decisions=targeted_pack_decisions,
        loss_count=loss_count,
        attempt_count=len(attempts),
        manual_stop=manual_stop,
        terminal_attempts=terminal_attempts,
        diagnostic_events=diagnostic_events,
    )


def _coverage_line(label: str, passed: bool, detail: str) -> str:
    return f"{label:<32} : {'PASS' if passed else 'PENDING'} — {detail}"


def render_release_report(report: ReleaseReport) -> str:
    phases = set(report.phases)
    has_core_flow = {
        "BLIND_SELECT",
        "SELECTING_HAND",
        "ROUND_EVAL",
        "SHOP",
    }.issubset(phases)
    has_pack = any(phase.endswith("_PACK") for phase in phases)
    repeated_losses = report.loss_count >= 2
    complete_attempt = report.terminal_attempts >= 1

    lines = [
        "=" * 78,
        "BALATRO v0.9G LIVE RELEASE REPORT",
        "=" * 78,
        f"Session                         : {report.session_id}",
        f"Artifact integrity              : {'PASS' if report.integrity_ok else 'FAIL'}",
        f"Attempts / losses               : {report.attempt_count} / {report.loss_count}",
        f"Diagnostic failure events       : {report.diagnostic_events}",
        f"Observed phases                 : {', '.join(report.phases) or '-'}",
        f"Observed actions                : {', '.join(report.actions) or '-'}",
        "",
        "LIVE COVERAGE",
        "-" * 78,
        _coverage_line(
            "Repeated loss -> restart",
            repeated_losses,
            f"losses observed={report.loss_count}; release target >=2",
        ),
        _coverage_line(
            "Manual cooperative OFF",
            report.manual_stop,
            "session ended by manual stop" if report.manual_stop else "not demonstrated in this session",
        ),
        _coverage_line(
            "Core production flow",
            has_core_flow,
            "blind-select/hand/round-eval/shop all observed",
        ),
        _coverage_line(
            "Pack subflow",
            has_pack,
            "at least one real *_PACK phase observed",
        ),
        _coverage_line(
            "D9 pack decision",
            report.pack_decisions > 0,
            f"pack-policy decisions observed={report.pack_decisions}",
        ),
        _coverage_line(
            "D10 targeted follow-up",
            report.targeted_pack_decisions > 0,
            f"targeted pack decisions observed={report.targeted_pack_decisions}",
        ),
        _coverage_line(
            "Complete real attempt",
            complete_attempt,
            f"terminal WIN/LOSS attempts observed={report.terminal_attempts}",
        ),
    ]

    if report.integrity_errors:
        lines.extend(["", "INTEGRITY ERRORS", "-" * 78])
        lines.extend(f"- {item}" for item in report.integrity_errors)
    if report.warnings:
        lines.extend(["", "WARNINGS", "-" * 78])
        lines.extend(f"- {item}" for item in report.warnings)

    if not report.integrity_ok:
        overall = "FAIL — repair artifacts/runtime before release"
    elif report.diagnostic_events:
        overall = "REVIEW — inspect diagnostic events before release"
    elif all(
        (
            repeated_losses,
            report.manual_stop,
            has_core_flow,
            has_pack,
            report.pack_decisions > 0,
            complete_attempt,
        )
    ):
        overall = (
            "LIVE EVIDENCE STRONG — D10 may remain encounter-dependent if no targeted "
            "pack appeared"
        )
    else:
        overall = "PENDING — artifact integrity is clean; more live coverage is required"

    lines.extend(["", f"Overall                         : {overall}"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only integrity and coverage report for a Balatro v0.9G live session."
    )
    parser.add_argument("--session-id")
    parser.add_argument("--session-directory", default="logs/balatro/sessions")
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    parser.add_argument("--diagnostic-directory", default="logs/balatro/diagnostics")
    args = parser.parse_args()

    try:
        report = build_release_report(
            session_id=args.session_id,
            session_directory=args.session_directory,
            run_log_directory=args.run_log_directory,
            diagnostic_directory=args.diagnostic_directory,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("Balatro v0.9G release report -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(render_release_report(report))
    return 0 if report.integrity_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
