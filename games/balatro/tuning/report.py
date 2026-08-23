from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def study_report(study) -> dict[str, Any]:
    completed = [trial for trial in study.trials if str(trial.state.name) == "COMPLETE"]
    failed = [trial for trial in study.trials if str(trial.state.name) == "FAIL"]
    pruned = [trial for trial in study.trials if str(trial.state.name) == "PRUNED"]
    best = study.best_trial if completed else None
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
        "best_trial": None if best is None else {
            "number": best.number,
            "value": best.value,
            "params": dict(best.params),
            "calibration": best.user_attrs.get("calibration"),
            "metrics": {
                key.removeprefix("metric."): value
                for key, value in best.user_attrs.items()
                if key.startswith("metric.")
            },
        },
    }


def write_study_report(study, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(study_report(study), indent=2, sort_keys=True), encoding="utf-8")
    return target
