from __future__ import annotations

"""Evaluate one code-level Balatro candidate against a frozen live baseline report.

This path is deliberately separate from Optuna calibration studies. A persistent
Optuna study is bound to one repository SHA; code changes therefore require their
own fresh authoritative batch while retaining the old production baseline as an
immutable external reference.
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION
from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator
from games.balatro.tuning.live_preflight import validate_live_tuning_preflight


REPORT_SCHEMA = "live-code-candidate-v1"


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository_sha() -> str:
    dirty = _git("status", "--porcelain")
    if dirty:
        raise RuntimeError(
            "live code-candidate evaluation requires a clean worktree so HEAD "
            "exactly describes the evaluated code"
        )
    sha = _git("rev-parse", "HEAD")
    if not sha:
        raise RuntimeError("could not resolve repository HEAD")
    return sha


def _numeric_delta(candidate: dict[str, object], baseline: dict[str, object]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in candidate.items():
        before = baseline.get(key)
        if isinstance(value, bool) or isinstance(before, bool):
            continue
        if isinstance(value, (int, float)) and isinstance(before, (int, float)):
            result[key] = float(value) - float(before)
    return result


def _load_reference_baseline(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    baseline = payload.get("production_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("reference report does not contain a production_baseline trial")
    if not bool(baseline.get("production_baseline")):
        raise ValueError("reference report production_baseline is not marked authoritative")
    repository_sha = str(baseline.get("repository_sha") or "").strip()
    metrics = baseline.get("metrics")
    if not repository_sha:
        raise ValueError("reference production baseline is missing repository_sha")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("reference production baseline is missing metrics")
    return {
        "repository_sha": repository_sha,
        "session_id": baseline.get("session_id"),
        "run_ids": list(baseline.get("run_ids") or ()),
        "metrics": dict(metrics),
        "study_name": payload.get("study_name"),
        "study_attrs": dict(payload.get("study_attrs") or {}),
    }


def _candidate_report(
    *,
    repository_sha: str,
    reference: dict[str, Any],
    evaluation,
    deck: str,
    stake: str,
) -> dict[str, Any]:
    candidate_metrics = evaluation.metrics.to_dict()
    baseline_metrics = dict(reference["metrics"])
    return {
        "schema": REPORT_SCHEMA,
        "mode": "authoritative-live-unseeded-code-candidate",
        "deck": str(deck).upper(),
        "stake": str(stake).upper(),
        "reference_baseline": {
            "repository_sha": reference["repository_sha"],
            "study_name": reference.get("study_name"),
            "session_id": reference.get("session_id"),
            "run_ids": list(reference.get("run_ids") or ()),
            "metrics": baseline_metrics,
        },
        "candidate": {
            "repository_sha": repository_sha,
            "calibration": DEFAULT_BOND_CALIBRATION.to_dict(),
            "session_id": str(evaluation.session_id),
            "run_ids": list(evaluation.run_ids),
            "won": bool(evaluation.won),
            "stop_reason": str(evaluation.stop_reason),
            "metrics": candidate_metrics,
        },
        "candidate_vs_baseline": {
            "objective_delta": float(candidate_metrics["objective"])
            - float(baseline_metrics["objective"]),
            "metric_deltas": _numeric_delta(candidate_metrics, baseline_metrics),
            "authoritative_live_warning": (
                "Unseeded live deltas are descriptive, not an automatic promotion gate; "
                "validate promising code candidates with another fresh batch before promotion."
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one authoritative unseeded live batch for the current code HEAD and "
            "compare it with an immutable production baseline study report."
        )
    )
    parser.add_argument(
        "--baseline-report",
        type=Path,
        default=Path("logs/balatro/tuning/study-report.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("logs/balatro/tuning/code-candidate-report.json"),
    )
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument(
        "--run-log-directory",
        type=Path,
        default=Path("logs/balatro/tuning/runs"),
    )
    parser.add_argument(
        "--session-directory",
        type=Path,
        default=Path("logs/balatro/tuning/sessions"),
    )
    parser.add_argument(
        "--control-directory",
        type=Path,
        default=Path("logs/balatro/tuning/control"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.attempts <= 0:
        raise SystemExit("--attempts must be positive")

    try:
        revision = _repository_sha()
        reference = _load_reference_baseline(args.baseline_report)
        if revision == reference["repository_sha"]:
            raise RuntimeError(
                "current HEAD is the same SHA as the frozen production baseline; "
                "use the baseline study rather than relabeling it as a code candidate"
            )

        attrs = reference.get("study_attrs", {})
        baseline_deck = str(attrs.get("deck") or args.deck).upper()
        baseline_stake = str(attrs.get("stake") or args.stake).upper()
        if baseline_deck != str(args.deck).upper() or baseline_stake != str(args.stake).upper():
            raise RuntimeError(
                "candidate deck/stake does not match reference baseline: "
                f"baseline={baseline_deck}/{baseline_stake}, "
                f"candidate={str(args.deck).upper()}/{str(args.stake).upper()}"
            )

        preflight = validate_live_tuning_preflight(
            expected_deck=args.deck,
            expected_stake=args.stake,
        )
    except Exception as error:
        print("Balatro live code candidate -> BLOCKED")
        print(f"Reason -> {error}")
        return 2

    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=args.attempts,
        deck=str(args.deck).upper(),
        stake=str(args.stake).upper(),
        run_log_directory=args.run_log_directory,
        session_directory=args.session_directory,
        control_directory=args.control_directory,
    )

    print("Balatro live code candidate -> PREFLIGHT PASS")
    print(f"Boundary -> {preflight.phase}, Ante {preflight.ante}, {preflight.deck}/{preflight.stake}")
    print(f"Candidate SHA -> {revision}")
    print(f"Reference baseline SHA -> {reference['repository_sha']}")

    try:
        evaluation = evaluator.evaluate(DEFAULT_BOND_CALIBRATION)
        payload = _candidate_report(
            repository_sha=revision,
            reference=reference,
            evaluation=evaluation,
            deck=args.deck,
            stake=args.stake,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception as error:
        print("Balatro live code candidate -> FAIL")
        print(f"Reason -> {error}")
        return 3

    delta = payload["candidate_vs_baseline"]["objective_delta"]
    print("Balatro live code candidate -> COMPLETE")
    print(f"Session -> {evaluation.session_id}")
    print(f"Runs -> {len(evaluation.run_ids)}")
    print(f"Won -> {bool(evaluation.won)}")
    print(f"Objective -> {evaluation.metrics.objective:.6f}")
    print(f"Objective delta vs frozen baseline -> {delta:+.6f}")
    print(f"Report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
