from __future__ import annotations

import json

import pytest

from games.balatro.live.run_diagnostics import BalatroDiagnosticLogger


def _rows(logger: BalatroDiagnosticLogger):
    return [
        json.loads(line)
        for line in logger.path.read_text(encoding="utf-8").splitlines()
    ]


def test_failure_diagnostics_are_separate_append_only_jsonl(tmp_path):
    diagnostic_dir = tmp_path / "diagnostics"
    logger = BalatroDiagnosticLogger("session-001", directory=diagnostic_dir)

    logger.failure(
        stage="execution_failure",
        error=RuntimeError("bridge rejected action"),
        status={"state": "ERROR", "last_error": "bridge rejected action"},
        action="PLAY_CARDS",
        phase="SELECTING_HAND",
        checkpoint_sequence=17,
    )

    assert logger.path == diagnostic_dir / "session-001.jsonl"
    rows = _rows(logger)
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "balatro-diagnostic-v1"
    assert row["session_id"] == "session-001"
    assert row["sequence"] == 1
    assert row["stage"] == "execution_failure"
    assert row["data"]["error_type"] == "RuntimeError"
    assert row["data"]["error"] == "bridge rejected action"
    assert row["data"]["action"] == "PLAY_CARDS"
    assert row["data"]["phase"] == "SELECTING_HAND"
    assert row["data"]["checkpoint_sequence"] == 17


def test_diagnostic_logger_resumes_contiguous_sequence(tmp_path):
    logger = BalatroDiagnosticLogger("session-002", directory=tmp_path)
    logger.record("first", value=1)

    resumed = BalatroDiagnosticLogger("session-002", directory=tmp_path)
    resumed.record("second", value=2)

    assert resumed.sequence == 2
    assert [row["sequence"] for row in _rows(resumed)] == [1, 2]
    assert [row["stage"] for row in _rows(resumed)] == ["first", "second"]


def test_diagnostic_logger_rejects_non_contiguous_existing_log(tmp_path):
    path = tmp_path / "session-bad.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": "balatro-diagnostic-v1",
                "session_id": "session-bad",
                "sequence": 2,
                "stage": "bad",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "data": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sequence is not contiguous"):
        BalatroDiagnosticLogger("session-bad", directory=tmp_path)


def test_diagnostic_logger_stringifies_non_json_values(tmp_path):
    logger = BalatroDiagnosticLogger("session-003", directory=tmp_path)
    logger.record("fixture", opaque=object())

    row = _rows(logger)[0]
    assert isinstance(row["data"]["opaque"], str)
