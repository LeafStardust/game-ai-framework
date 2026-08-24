import json
from types import SimpleNamespace

import pytest

from balatro_evaluate_code_candidate_live import (
    REPORT_SCHEMA,
    _candidate_report,
    _load_reference_baseline,
)


class _Metrics:
    def __init__(self, values):
        self.values = dict(values)

    def to_dict(self):
        return dict(self.values)


def _baseline_payload():
    return {
        "study_name": "red-white-production-baseline",
        "study_attrs": {
            "deck": "RED",
            "stake": "WHITE",
            "mode": "authoritative-live-unseeded",
        },
        "production_baseline": {
            "production_baseline": True,
            "repository_sha": "baseline-sha",
            "session_id": "baseline-session",
            "run_ids": ["run-a", "run-b", "run-c"],
            "metrics": {
                "objective": 22.5,
                "win_rate": 0.0,
                "average_ante": 4.0,
            },
        },
    }


def test_load_reference_baseline_preserves_frozen_provenance(tmp_path):
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(_baseline_payload()), encoding="utf-8")

    baseline = _load_reference_baseline(path)

    assert baseline["repository_sha"] == "baseline-sha"
    assert baseline["session_id"] == "baseline-session"
    assert baseline["run_ids"] == ["run-a", "run-b", "run-c"]
    assert baseline["metrics"]["objective"] == 22.5
    assert baseline["study_attrs"]["deck"] == "RED"


def test_load_reference_baseline_rejects_nonbaseline_report(tmp_path):
    payload = _baseline_payload()
    payload["production_baseline"]["production_baseline"] = False
    path = tmp_path / "not-baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not marked authoritative"):
        _load_reference_baseline(path)


def test_code_candidate_report_keeps_reference_separate_and_computes_deltas():
    reference = {
        "repository_sha": "baseline-sha",
        "study_name": "baseline-study",
        "session_id": "baseline-session",
        "run_ids": ["run-a", "run-b", "run-c"],
        "metrics": {
            "objective": 22.5,
            "win_rate": 0.0,
            "average_ante": 4.0,
        },
    }
    evaluation = SimpleNamespace(
        metrics=_Metrics(
            {
                "objective": 30.0,
                "win_rate": 1.0 / 3.0,
                "average_ante": 5.0,
            }
        ),
        session_id="candidate-session",
        run_ids=("run-d", "run-e", "run-f"),
        won=True,
        stop_reason="WIN",
    )

    report = _candidate_report(
        repository_sha="candidate-sha",
        reference=reference,
        evaluation=evaluation,
        deck="RED",
        stake="WHITE",
    )

    assert report["schema"] == REPORT_SCHEMA
    assert report["reference_baseline"]["repository_sha"] == "baseline-sha"
    assert report["candidate"]["repository_sha"] == "candidate-sha"
    assert report["candidate"]["run_ids"] == ["run-d", "run-e", "run-f"]
    assert report["candidate_vs_baseline"]["objective_delta"] == pytest.approx(7.5)
    assert report["candidate_vs_baseline"]["metric_deltas"]["average_ante"] == pytest.approx(1.0)
