from __future__ import annotations

import argparse
import traceback

from .agent_control import BalatroAgentControl
from .balatro_agent_crash_report_repo import write_repo_crash_report
from .balatro_agent_supervisor import BalatroAgentSupervisor


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the toggleable Balatro autonomous supervisor with automatic "
            "traceback and crash-report capture on unhandled failures."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    parser.add_argument("--session-directory", default="logs/balatro/sessions")
    parser.add_argument("--session-id")
    parser.add_argument("--no-retry-losses", action="store_true")
    args = parser.parse_args()

    control = BalatroAgentControl(args.control_dir)
    supervisor = BalatroAgentSupervisor(
        control=control,
        run_log_directory=args.run_log_directory,
        session_directory=args.session_directory,
        session_id=args.session_id,
        retry_losses=not args.no_retry_losses,
    )

    try:
        result = supervisor.run()
    except Exception as error:
        exception_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        print("Balatro autonomous supervisor -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        print("Traceback ->")
        print(exception_text.rstrip())
        try:
            report_path, _ = write_repo_crash_report(
                control,
                exception_text=exception_text,
            )
            print(f"Crash report -> {report_path}")
        except Exception as report_error:
            print(
                "Crash report -> FAILED "
                f"({type(report_error).__name__}: {report_error})"
            )
        return 2

    print("Balatro autonomous supervisor -> OFF")
    print(f"Session -> {result.session_id}")
    print(f"Attempts -> {len(result.attempts)}")
    print(f"Won -> {result.won}")
    print(f"Stop reason -> {result.stop_reason}")
    print(f"Session summary -> {result.summary_path}")
    if result.stop_reason.startswith("RESTART_FAILED:"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
