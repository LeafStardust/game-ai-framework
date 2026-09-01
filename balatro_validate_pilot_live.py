from __future__ import annotations

"""Run the fixed-production three-Bond pilot against the real Balatro game.

This is validation, not tuning: it always uses DEFAULT_BOND_CALIBRATION and does
not create an Optuna study or sample any candidate parameters. The authoritative
live evaluator still owns preflight, the bounded production supervisor, durable
run/session logs, shop diagnostics, and guarded reset after an all-loss batch.
"""

import argparse
import json
import subprocess
from pathlib import Path

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION
from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator


_DEFAULT_ROOT = Path("logs/balatro/pilot-live")


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
            "pilot live validation requires a clean worktree so the recorded commit "
            "SHA exactly describes the evaluated production agent"
        )
    sha = _git("rev-parse", "HEAD")
    if not sha:
        raise RuntimeError("could not resolve repository HEAD")
    return sha


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded Red/White production-baseline batch for the refurbished "
            "Burnt, Deck-Thinning, and Held-card/Steel Bond pilot."
        )
    )
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument("--output-directory", type=Path, default=_DEFAULT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.attempts <= 0:
        raise SystemExit("--attempts must be positive")

    root = args.output_directory
    run_directory = root / "runs"
    session_directory = root / "sessions"
    control_directory = root / "control"
    report_path = root / "latest-report.json"

    try:
        revision = _repository_sha()
        evaluator = AuthoritativeLiveBatchEvaluator(
            attempts_per_trial=int(args.attempts),
            deck=str(args.deck).upper(),
            stake=str(args.stake).upper(),
            run_log_directory=run_directory,
            session_directory=session_directory,
            control_directory=control_directory,
        )
        result = evaluator.evaluate(DEFAULT_BOND_CALIBRATION)
    except Exception as error:
        print("Balatro three-Bond pilot live validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    payload = {
        "repository_sha": revision,
        "deck": str(args.deck).upper(),
        "stake": str(args.stake).upper(),
        "requested_attempts": int(args.attempts),
        "completed_attempts": len(result.run_ids),
        "session_id": result.session_id,
        "run_ids": list(result.run_ids),
        "won": bool(result.won),
        "stop_reason": result.stop_reason,
        "metrics": result.metrics.to_dict(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Balatro three-Bond pilot live validation -> COMPLETE")
    print(f"Repository SHA -> {revision}")
    print(f"Boundary -> {str(args.deck).upper()} / {str(args.stake).upper()}")
    print(f"Session -> {result.session_id}")
    print(f"Attempts -> {len(result.run_ids)}/{int(args.attempts)}")
    print(f"Won -> {bool(result.won)}")
    print(f"Stop reason -> {result.stop_reason}")
    print(f"Win rate -> {result.metrics.win_rate:.3f}")
    print(f"Average ante -> {result.metrics.average_ante:.3f}")
    print(f"Median ante -> {result.metrics.median_ante:.3f}")
    print(f"Power-engine utilization -> {result.metrics.mean('power_engine_utilization'):.3f}")
    print(f"Unused active engines -> {result.metrics.mean('unused_active_engine_count'):.3f}")
    print(f"Destructive pivots -> {result.metrics.mean('destructive_pivot_count'):.3f}")
    print(f"Illegal actions -> {result.metrics.mean('illegal_action_count'):.3f}")
    print(f"Run IDs -> {', '.join(result.run_ids)}")
    print(f"Report -> {report_path}")
    print(f"Run logs -> {run_directory}")
    print(f"Session logs -> {session_directory}")
    print(f"Control/shop traces -> {control_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
