from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.tuning.metrics import BatchMetrics, EpisodeMetrics
from games.balatro.tuning.study import LiveStudyConfig, make_live_phase_a_objective


class _Trial:
    def __init__(self, *, defaults=None):
        self.user_attrs = {}
        self.defaults = defaults or {}

    def suggest_float(self, name, low, high):
        defaults = {
            "pivot_resistance_r1": 0.5,
            "pivot_resistance_r2_delta": 0.5,
            "pivot_resistance_r3_delta": 1.5,
            "pivot_resistance_r4_delta": 2.0,
            "pivot_resistance_r5_delta": 2.5,
            "realization_priority_weight": 0.75,
            "synergy_bonus": 1.5,
            "conflict_penalty": 2.0,
        }
        defaults.update(self.defaults)
        value = defaults[name]
        assert low <= value <= high
        return value

    def set_user_attr(self, key, value):
        self.user_attrs[key] = value


class _Evaluator:
    def __init__(self, *, run_ids=("run-1",), metrics=None):
        self.run_ids = run_ids
        self.metrics = metrics or BatchMetrics.from_episodes(
            [EpisodeMetrics(seed=None, won=False, ante_reached=5, build_signature="burnt")]
        )

    def evaluate(self, calibration):
        return SimpleNamespace(
            metrics=self.metrics,
            session_id="session-1",
            run_ids=self.run_ids,
            won=False,
            stop_reason="attempt limit reached",
        )


def _config(tmp_path: Path, **kwargs):
    values = {
        "name": "live",
        "storage_path": tmp_path / "study.sqlite3",
        "repository_sha": "abc123",
        "attempts_per_trial": 5,
    }
    values.update(kwargs)
    return LiveStudyConfig(**values)


def test_live_objective_records_unseeded_session_run_calibration_and_metrics(tmp_path: Path):
    trial = _Trial()
    value = make_live_phase_a_objective(_config(tmp_path), _Evaluator())(trial)

    assert isinstance(value, float)
    assert trial.user_attrs["repository_sha"] == "abc123"
    assert trial.user_attrs["session_id"] == "session-1"
    assert trial.user_attrs["run_ids"] == ["run-1"]
    assert trial.user_attrs["unseeded"] is True
    assert trial.user_attrs["won"] is False
    assert trial.user_attrs["stop_reason"] == "attempt limit reached"
    assert trial.user_attrs["production_baseline"] is True
    assert trial.user_attrs["metric.episodes"] == 1
    assert trial.user_attrs["metric.average_ante"] == 5.0
    calibration = trial.user_attrs["calibration"]
    assert calibration["schema_version"] == 1
    assert calibration["synergy_bonus"] == pytest.approx(1.5)
    assert calibration["pivot_resistance_r5"] == pytest.approx(7.0)


def test_live_objective_marks_nondefault_candidate_as_not_baseline(tmp_path: Path):
    trial = _Trial(defaults={"synergy_bonus": 1.75})
    make_live_phase_a_objective(_config(tmp_path), _Evaluator())(trial)
    assert trial.user_attrs["production_baseline"] is False
    assert trial.user_attrs["calibration"]["synergy_bonus"] == pytest.approx(1.75)


def test_live_objective_rejects_missing_run_provenance(tmp_path: Path):
    with pytest.raises(RuntimeError, match="no run provenance"):
        make_live_phase_a_objective(_config(tmp_path), _Evaluator(run_ids=()))(_Trial())


def test_live_objective_rejects_non_batch_metrics(tmp_path: Path):
    evaluator = _Evaluator(metrics=SimpleNamespace())
    with pytest.raises(TypeError, match="BatchMetrics"):
        make_live_phase_a_objective(_config(tmp_path), evaluator)(_Trial())


def test_live_study_config_rejects_invalid_identity_or_attempt_count(tmp_path: Path):
    with pytest.raises(ValueError, match="study name"):
        _config(tmp_path, name="")
    with pytest.raises(ValueError, match="repository SHA"):
        _config(tmp_path, repository_sha="")
    with pytest.raises(ValueError, match="attempts_per_trial"):
        _config(tmp_path, attempts_per_trial=0)


def test_live_study_storage_url_is_persistent_sqlite_path(tmp_path: Path):
    config = _config(tmp_path)
    assert config.storage_url.startswith("sqlite:///")
    assert config.storage_url.endswith("study.sqlite3")
    assert (tmp_path).exists()
