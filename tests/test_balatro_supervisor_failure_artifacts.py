from __future__ import annotations

import json
import sys
from pathlib import Path

from games.balatro.live.runtime import balatro_agent_supervisor_entry as entry


class _Control:
    def __init__(self, root):
        self.root = root

    def read_status(self):
        return {
            "state": "ERROR",
            "last_error": "fixture supervisor failure",
        }


class _FailingSupervisor:
    def __init__(self, **kwargs):
        self.session_id = kwargs.get("session_id") or "session-failure-test"
        self.session_directory = Path(kwargs["session_directory"])
        self.summary_calls = []

    def run(self):
        raise RuntimeError("fixture supervisor failure")

    def _write_summary(self, *, won, stop_reason):
        self.summary_calls.append((won, stop_reason))
        self.session_directory.mkdir(parents=True, exist_ok=True)
        path = self.session_directory / f"{self.session_id}.summary.json"
        path.write_text(
            json.dumps(
                {
                    "session_id": self.session_id,
                    "won": bool(won),
                    "stop_reason": stop_reason,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return path


def test_unhandled_supervisor_failure_writes_diagnostic_and_summary(
    tmp_path,
    monkeypatch,
):
    control_dir = tmp_path / "control"
    run_dir = tmp_path / "runs"
    session_dir = tmp_path / "sessions"
    diagnostic_dir = tmp_path / "diagnostics"
    report_path = tmp_path / "crash-report.txt"

    monkeypatch.setattr(entry, "BalatroAgentControl", _Control)
    monkeypatch.setattr(entry, "BalatroAgentSupervisor", _FailingSupervisor)
    monkeypatch.setattr(
        entry,
        "write_repo_crash_report",
        lambda control, exception_text=None: (report_path, "fixture"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "balatro-agent-supervisor",
            "--control-dir",
            str(control_dir),
            "--run-log-directory",
            str(run_dir),
            "--session-directory",
            str(session_dir),
            "--diagnostic-directory",
            str(diagnostic_dir),
            "--session-id",
            "session-failure-test",
        ],
    )

    assert entry.main() == 2

    summary_path = session_dir / "session-failure-test.summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["won"] is False
    assert "supervisor failure: fixture supervisor failure" in summary["stop_reason"]

    diagnostic_path = diagnostic_dir / "session-failure-test.jsonl"
    assert diagnostic_path.exists()
    rows = [
        json.loads(line)
        for line in diagnostic_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["stage"] == "supervisor_failure"
    assert rows[0]["data"]["error_type"] == "RuntimeError"
    assert rows[0]["data"]["status"]["state"] == "ERROR"
