from __future__ import annotations

"""Run authoritative unseeded Optuna Bond calibration against the real game."""

import argparse
import subprocess
from pathlib import Path

from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator
from games.balatro.tuning.live_preflight import validate_live_tuning_preflight
from games.balatro.tuning.report import write_study_report
from games.balatro.tuning.study import (
    LiveStudyConfig,
    create_live_phase_a_study,
    enqueue_production_baseline,
    make_live_phase_a_objective,
)


_TUNING_DIRECTORY = Path("logs/balatro/tuning")


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
    parser.add_argument("--storage", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--repo-sha", help="override clean-worktree HEAD provenance")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument(
        "--attempts-per-trial",
        type=int,
        default=3,
        help="authoritative runs per exploratory trial; use larger fresh batches for promotion/holdout",
    )
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--sampler-seed", type=int, default=20260823)
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help=(
            "run exactly the queued production-default baseline trial and stop; "
            "requires a fresh study with zero existing trials"
        ),
    )
    parser.add_argument("--run-log-directory", type=Path)
    parser.add_argument("--session-directory", type=Path)
    parser.add_argument("--control-directory", type=Path)
    return parser


def run_live_phase_a(
    config: LiveStudyConfig,
    evaluator,
    *,
    trials: int,
    timeout_seconds: float | None = None,
):
    """Run live trials on one persistent Study/sampler for this invocation."""
    if trials <= 0:
        raise ValueError("trials must be positive")

    study = create_live_phase_a_study(config)
    enqueue_production_baseline(study)
    objective = make_live_phase_a_objective(config, evaluator)

    # Optimize one trial at a time on the SAME Study/sampler so a real win can
    # stop before the guarded evaluator is asked to operate on a won terminal
    # frame. Recreating the Study here per trial would reset the seeded sampler
    # and repeat the same candidate proposal.
    for _ in range(trials):
        study.optimize(
            objective,
            n_trials=1,
            timeout=timeout_seconds,
            gc_after_trial=True,
            catch=(RuntimeError,),
        )
        latest = study.trials[-1]
        if bool(latest.user_attrs.get("won")):
            break
    return study


def main() -> int:
    args = build_parser().parse_args()
    if args.trials <= 0:
        raise SystemExit("--trials must be positive")
    if args.attempts_per_trial <= 0:
        raise SystemExit("--attempts-per-trial must be positive")

    storage_path = args.storage or (_TUNING_DIRECTORY / "optuna.sqlite3")
    report_path = args.report or (_TUNING_DIRECTORY / "study-report.json")
    run_log_directory = args.run_log_directory or (_TUNING_DIRECTORY / "runs")
    session_directory = args.session_directory or (_TUNING_DIRECTORY / "sessions")
    control_directory = args.control_directory or (_TUNING_DIRECTORY / "control")

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
        storage_path=storage_path,
        repository_sha=revision,
        attempts_per_trial=args.attempts_per_trial,
        deck=str(args.deck).upper(),
        stake=str(args.stake).upper(),
        sampler_seed=args.sampler_seed,
    )

    # Baseline-only has an extra safety contract: reject a reused study before
    # the live evaluator is constructed. The precheck must remain side-effect free;
    # run_live_phase_a owns baseline enqueue/execution on its persistent Study.
    if args.baseline_only:
        try:
            precheck_study = create_live_phase_a_study(config)
            if precheck_study.trials:
                print("Balatro live Bond tuning -> BLOCKED")
                print(
                    "Reason -> --baseline-only requires a fresh study with zero existing trials; "
                    f"study {config.name!r} already has {len(precheck_study.trials)} trial(s)"
                )
                return 2
        except Exception as error:
            print("Balatro live Bond tuning -> BLOCKED")
            print(f"Reason -> {error}")
            return 2

    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=args.attempts_per_trial,
        deck=config.deck,
        stake=config.stake,
        run_log_directory=run_log_directory,
        session_directory=session_directory,
        control_directory=control_directory,
    )

    print("Balatro live Bond tuning -> PREFLIGHT PASS")
    print(f"Boundary -> {preflight.phase}, Ante {preflight.ante}, {preflight.deck}/{preflight.stake}")
    print(f"Bridge -> protocol {preflight.bridge_version}, revision {preflight.bridge_revision}")
    print(f"Achievement gate -> {preflight.achievement_gate}")
    print(f"Storage -> {storage_path}")

    requested_trials = 1 if args.baseline_only else args.trials
    study = None
    try:
        study = run_live_phase_a(
            config,
            evaluator,
            trials=requested_trials,
            timeout_seconds=args.timeout_seconds,
        )
        latest = study.trials[-1]
        if args.baseline_only:
            if str(latest.state.name) != "COMPLETE":
                raise RuntimeError("production baseline trial did not complete")
            if not bool(latest.user_attrs.get("production_baseline")):
                raise RuntimeError("queued production baseline was not executed")
    except Exception as error:
        print("Balatro live Bond tuning -> FAIL")
        print(f"Reason -> {error}")
        if study is not None:
            write_study_report(study, report_path)
            print(f"Partial report -> {report_path}")
        return 3

    target = write_study_report(study, report_path)
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
