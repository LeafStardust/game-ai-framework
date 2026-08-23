from pathlib import Path
from types import SimpleNamespace
import json

from games.balatro.tuning.report import study_report, write_study_report


class _State:
    def __init__(self, name):
        self.name = name


def _trial(number, value, *, baseline=False, won=False):
    return SimpleNamespace(
        number=number,
        value=value,
        params={"synergy_bonus": 1.5 + 0.1 * number},
        state=_State("COMPLETE"),
        user_attrs={
            "production_baseline": baseline,
            "calibration": {"schema_version": 1, "synergy_bonus": 1.5 + 0.1 * number},
            "metric.objective": value,
            "metric.win_rate": 0.1 + 0.1 * number,
            "metric.average_ante": 4.0 + number,
            "repository_sha": "abc",
            "session_id": f"session-{number}",
            "run_ids": [f"run-{number}"],
            "won": won,
            "stop_reason": "done",
            "unseeded": True,
        },
    )


class _Study:
    study_name = "live"
    direction = SimpleNamespace(name="MAXIMIZE")
    user_attrs = {"mode": "authoritative-live-unseeded"}

    def __init__(self):
        self.trials = [_trial(0, 10.0, baseline=True), _trial(1, 15.0)]
        self.best_trial = self.trials[1]


def test_report_exposes_baseline_best_delta_and_live_warning():
    report = study_report(_Study())
    assert report["production_baseline"]["number"] == 0
    assert report["production_baseline"]["production_baseline"] is True
    assert report["best_trial"]["number"] == 1
    assert report["best_vs_baseline"]["objective_delta"] == 5.0
    assert report["best_vs_baseline"]["metric_deltas"]["average_ante"] == 1.0
    assert "not an automatic promotion gate" in report["best_vs_baseline"]["authoritative_live_warning"]
    assert len(report["completed_trials"]) == 2


def test_report_writer_persists_json(tmp_path: Path):
    target = write_study_report(_Study(), tmp_path / "report.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["study_name"] == "live"
    assert payload["best_trial"]["session_id"] == "session-1"


def test_report_handles_no_completed_trials():
    study = SimpleNamespace(
        study_name="empty",
        direction=SimpleNamespace(name="MAXIMIZE"),
        user_attrs={"mode": "seeded"},
        trials=[SimpleNamespace(state=_State("FAIL"))],
    )
    report = study_report(study)
    assert report["production_baseline"] is None
    assert report["best_trial"] is None
    assert report["best_vs_baseline"] is None
