from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _metrics(trial) -> dict[str, object]:
    return {
        key.removeprefix("metric."): value
        for key, value in trial.user_attrs.items()
        if key.startswith("metric.")
    }


def _trial_payload(trial) -> dict[str, Any]:
    return {
        "number": trial.number,
        "value": trial.value,
        "params": dict(trial.params),
        "calibration": trial.user_attrs.get("calibration"),
        "metrics": _metrics(trial),
        "production_baseline": bool(trial.user_attrs.get("production_baseline")),
        "repository_sha": trial.user_attrs.get("repository_sha"),
        "session_id": trial.user_attrs.get("session_id"),
        "run_ids": trial.user_attrs.get("run_ids"),
        "won": trial.user_attrs.get("won"),
        "stop_reason": trial.user_attrs.get("stop_reason"),
        "unseeded": trial.user_attrs.get("unseeded"),
    }


def _baseline_trial(completed):
    return next(
        (trial for trial in completed if bool(trial.user_attrs.get("production_baseline"))),
        None,
    )


def _numeric_delta(candidate: dict[str, object], baseline: dict[str, object]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in candidate.items():
        before = baseline.get(key)
        if isinstance(value, bool) or isinstance(before, bool):
            continue
        if isinstance(value, (int, float)) and isinstance(before, (int, float)):
            result[key] = float(value) - float(before)
    return result


def study_report(study) -> dict[str, Any]:
    completed = [trial for trial in study.trials if str(trial.state.name) == "COMPLETE"]
    failed = [trial for trial in study.trials if str(trial.state.name) == "FAIL"]
    pruned = [trial for trial in study.trials if str(trial.state.name) == "PRUNED"]
    best = study.best_trial if completed else None
    baseline = _baseline_trial(completed)
    baseline_metrics = _metrics(baseline) if baseline is not None else {}
    best_metrics = _metrics(best) if best is not None else {}

    return {
        "study_name": study.study_name,
        "direction": str(study.direction.name),
        "study_attrs": dict(study.user_attrs),
        "trial_counts": {
            "total": len(study.trials),
            "complete": len(completed),
            "failed": len(failed),
            "pruned": len(pruned),
        },
        "production_baseline": None if baseline is None else _trial_payload(baseline),
        "best_trial": None if best is None else _trial_payload(best),
        "best_vs_baseline": None if baseline is None or best is None else {
            "objective_delta": float(best.value) - float(baseline.value),
            "metric_deltas": _numeric_delta(best_metrics, baseline_metrics),
            "comparable_mode": study.user_attrs.get("mode"),
            "authoritative_live_warning": (
                "Unseeded live deltas are descriptive, not an automatic promotion gate; "
                "repeat candidate/baseline batches or seeded holdout validation before promotion."
                if study.user_attrs.get("mode") == "authoritative-live-unseeded"
                else None
            ),
        },
        "completed_trials": [_trial_payload(trial) for trial in completed],
    }


def write_study_report(study, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(study_report(study), indent=2, sort_keys=True), encoding="utf-8")
    return target
