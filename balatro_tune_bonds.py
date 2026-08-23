from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from games.balatro.tuning.report import write_study_report
from games.balatro.tuning.study import StudyConfig, run_phase_a


def _load_evaluator(spec: str):
    if ":" not in spec:
        raise ValueError("evaluator must use module:function syntax")
    module_name, function_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    evaluator = getattr(module, function_name, None)
    if not callable(evaluator):
        raise ValueError(f"evaluator {spec!r} is not callable")
    return evaluator


def _parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    if len(set(seeds)) != len(seeds):
        raise argparse.ArgumentTypeError("seeds must be unique")
    return seeds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an offline Optuna study over Balatro Bond calibration parameters."
    )
    parser.add_argument("--evaluator", required=True, help="Batch evaluator as module:function")
    parser.add_argument("--study", required=True, help="Persistent Optuna study name")
    parser.add_argument("--storage", type=Path, required=True, help="SQLite study database path")
    parser.add_argument("--report", type=Path, required=True, help="JSON report output path")
    parser.add_argument("--repo-sha", required=True, help="Exact repository revision under evaluation")
    parser.add_argument("--seeds", type=_parse_seeds, required=True, help="Comma-separated fixed seed schedule")
    parser.add_argument("--trials", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument("--sampler-seed", type=int, default=20260823)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    evaluator = _load_evaluator(args.evaluator)
    config = StudyConfig(
        name=args.study,
        storage_path=args.storage,
        seeds=args.seeds,
        repository_sha=args.repo_sha,
        deck=args.deck,
        stake=args.stake,
        sampler_seed=args.sampler_seed,
    )
    study = run_phase_a(
        config,
        evaluator,
        trials=args.trials,
        timeout_seconds=args.timeout_seconds,
    )
    target = write_study_report(study, args.report)
    print(f"Study: {study.study_name}")
    print(f"Trials: {len(study.trials)}")
    print(f"Best objective: {study.best_value:.6f}")
    print(f"Report: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
