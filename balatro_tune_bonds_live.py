from __future__ import annotations

"""Run authoritative unseeded Optuna Bond calibration against the real game."""

import argparse
import subprocess
from pathlib import Path

from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator
from games.balatro.tuning.live_preflight import validate_live_tuning_preflight
from games.balatro.tuning.report import write_study_report
from games.balatro.tuning.study import LiveStudyConfig, run_live_phase_a


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository_sha(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    dirty = _git("status", "--porcelain")
    if dirty:
        raise RuntimeError(
            "live tuning requires a clean worktree so the recorded commit SHA exactly "
            "describes the evaluated code"
        )
    sha = _git("rev-parse", "HEAD")
    if not sha:
        raise RuntimeError("could not resolve repository HEAD")
    return sha


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Tune Phase-A Balatro Bond composition constants through authoritative "
            "unseeded live runs. Every trial must begin at a fresh Ante-1 BLIND_SELECT "
            "boundary. Lost trial batches reset automatically; a winning trial stops "
            "the study for review/holdout validation."
        )
    )
    parser.add_argument("--study", required=True)
    parser.add_argument(
        "--storage",
        type=Path,
        default=Path("logs/balatro/tuning/optuna.sqlite3"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("logs/balatro/tuning/study-report.json"),
    )
    parser.add_argument("--repo-sha", help="override clean-worktree HEAD provenance")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--attempts-per-trial", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--sampler-seed", type=int, default=20260823)
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help=(
            "run exactly the queued production-default baseline trial and stop; "
            "use this before beginning a new live search campaign"
        ),
    )
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
    if args.trials <= 0:
        raise SystemExit("--trials must be positive")
    if args.attempts_per_trial <= 0:
        raise SystemExit("--attempts-per-trial must be positive")

    try:
        revision = _repository_sha(args.repo_sha)
        preflight = validate_live_tuning_preflight(
            expected_deck=args.deck,
            expected_stake=args.stake,
        )
    except Exception as error:
        print("Balatro live Bond tuning -> BLOCKED")
        print(f"Reason -> {error}")
        return 2

    config = LiveStudyConfig(
        name=args.study,
        storage_path=args.storage,
        repository_sha=revision,
        attempts_per_trial=args.attempts_per_trial,
        deck=str(args.deck).upper(),
        stake=str(args.stake).upper(),
        sampler_seed=args.sampler_seed,
    )
    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=args.attempts_per_trial,
        deck=config.deck,
        stake=config.stake,
        run_log_directory=args.run_log_directory,
        session_directory=args.session_directory,
        control_directory=args.control_directory,
    )

    print("Balatro live Bond tuning -> PREFLIGHT PASS")
    print(f"Boundary -> {preflight.phase}, Ante {preflight.ante}, {preflight.deck}/{preflight.stake}")
    print(f"Bridge -> protocol {preflight.bridge_version}, revision {preflight.bridge_revision}")
    print(f"Achievement gate -> {preflight.achievement_gate}")

    requested_trials = 1 if args.baseline_only else args.trials
    study = None
    try:
        # Optimize one trial at a time so a real win can stop before Optuna asks the
        # guarded live evaluator to operate on an intentionally non-restartable won
        # terminal frame. Lost batches restore BLIND_SELECT themselves; the evaluator
        # preflights that restored boundary again before every subsequent trial.
        for _ in range(requested_trials):
            study = run_live_phase_a(
                config,
                evaluator,
                trials=1,
                timeout_seconds=args.timeout_seconds,
            )
            latest = study.trials[-1]
            if args.baseline_only:
                if str(latest.state.name) != "COMPLETE":
                    raise RuntimeError("production baseline trial did not complete")
                if not bool(latest.user_attrs.get("production_baseline")):
                    raise RuntimeError(
                        "--baseline-only requires a fresh study whose next queued trial "
                        "is the production baseline"
                    )
                break
            if bool(latest.user_attrs.get("won")):
                break
    except Exception as error:
        print("Balatro live Bond tuning -> FAIL")
        print(f"Reason -> {error}")
        if study is not None:
            write_study_report(study, args.report)
            print(f"Partial report -> {args.report}")
        return 3

    assert study is not None
    target = write_study_report(study, args.report)
    latest = study.trials[-1]
    print("Balatro live Bond tuning -> COMPLETE")
    print(f"Study -> {study.study_name}")
    print(f"Repository SHA -> {revision}")
    print(f"Trials recorded -> {len(study.trials)}")
    print(f"Best objective -> {study.best_value:.6f}")
    print(f"Latest session -> {latest.user_attrs.get('session_id', '?')}")
    print(f"Latest production baseline -> {bool(latest.user_attrs.get('production_baseline'))}")
    print(f"Latest won -> {bool(latest.user_attrs.get('won'))}")
    print(f"Report -> {target}")
    if args.baseline_only:
        print("Next gate -> inspect baseline report, then start Phase-A candidate trials")
    elif bool(latest.user_attrs.get("won")):
        print("Next gate -> holdout/manual review; won runs are never auto-restarted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
