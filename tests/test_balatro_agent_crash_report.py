from __future__ import annotations

import json

import pytest

from games.balatro.live.external import balatro_agent_crash_report as report_module
from games.balatro.live.external import balatro_agent_toggle as toggle_module
from games.balatro.live.external.agent_control import BalatroAgentControl
from games.balatro.live.external.balatro_agent_crash_report import write_crash_report
from games.balatro.live.external.balatro_agent_supervisor import BalatroAgentSupervisor
from games.balatro.live.protocol import LiveBalatroSnapshot


def test_crash_report_collects_status_attempt_logs_and_agent_tail(tmp_path, monkeypatch):
    control = BalatroAgentControl(tmp_path / "control")
    control.write_status(
        "OFF",
        session_id="session-crash",
        attempt=2,
        run_id="session-crash-attempt-002",
        deck="RED",
        stake="WHITE",
        reason="supervisor failure: boom",
    )
    control.ensure_directory()
    (control.directory / "agent.log").write_text(
        "old line\nTraceback line\nRuntimeError: boom\n",
        encoding="utf-8",
    )

    session_dir = tmp_path / "logs" / "balatro" / "sessions"
    run_dir = tmp_path / "logs" / "balatro" / "runs"
    session_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    (session_dir / "session-crash.summary.json").write_text(
        json.dumps({"attempt_count": 2, "won": False}),
        encoding="utf-8",
    )
    (run_dir / "session-crash-attempt-002.jsonl").write_text(
        '{"event":"decision","sequence":7}\n',
        encoding="utf-8",
    )
    (run_dir / "session-crash-attempt-002.summary.json").write_text(
        json.dumps({"won": False, "reason": "game_over"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(report_module, "_git_value", lambda *_args: "test-git")
    monkeypatch.setattr(report_module, "_balatro_process_section", lambda: "balatro-process-test")
    monkeypatch.setattr(report_module, "_snapshot_section", lambda: "snapshot-test")
    monkeypatch.setattr(report_module, "_bridge_files_section", lambda: "bridge-test")
    monkeypatch.setattr(report_module, "_windows_events_section", lambda: "windows-test")

    path, report = write_crash_report(
        control,
        output_path=tmp_path / "report.txt",
        exception_text="RuntimeError: boom",
    )

    assert path.exists()
    assert path.read_text(encoding="utf-8") == report
    assert '"run_id": "session-crash-attempt-002"' in report
    assert "supervisor failure: boom" in report
    assert "balatro-process-test" in report
    assert "snapshot-test" in report
    assert "bridge-test" in report
    assert '"event":"decision","sequence":7' in report
    assert "RuntimeError: boom" in report
    assert "windows-test" in report


def test_toggle_uses_crash_reporting_supervisor_entrypoint():
    assert toggle_module.SUPERVISOR_MODULE.endswith("balatro_agent_supervisor_entry")


class _StableObserver:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def observe(self):
        return LiveBalatroSnapshot(
            sequence=1,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": False,
                "hand": {"cards": []},
            },
        )


class _CrashingRunner:
    def __init__(self, observer):
        self.observer = observer

    def decide(self):
        raise RuntimeError("planned crash")


def test_supervisor_failure_preserves_active_attempt_metadata(tmp_path):
    control = BalatroAgentControl(tmp_path / "control")
    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=_StableObserver,
        runner_factory=_CrashingRunner,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
        session_id="failure-metadata",
        startup_stability_interval_seconds=0.0,
    )

    with pytest.raises(RuntimeError, match="planned crash"):
        supervisor.run()

    status = control.read_status()
    assert status["state"] == "OFF"
    assert status["attempt"] == 1
    assert status["run_id"] == "failure-metadata-attempt-001"
    assert status["deck"] == "RED"
    assert status["stake"] == "WHITE"
    assert status["playbook"] == "red-white"
    assert "planned crash" in status["reason"]
