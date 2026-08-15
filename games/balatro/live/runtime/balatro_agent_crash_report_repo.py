from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .agent_control import BalatroAgentControl
from .balatro_agent_crash_report import (
    DEFAULT_AGENT_LOG_LINES,
    write_crash_report,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_repo_crash_report_path() -> Path:
    """Return the ignored, repository-local path for a new crash report."""
    return (
        _repo_root()
        / "logs"
        / "balatro"
        / "crash-reports"
        / f"balatro-agent-crash-{_stamp()}.log"
    )


def write_repo_crash_report(
    control: BalatroAgentControl | None = None,
    *,
    agent_log_lines: int = DEFAULT_AGENT_LOG_LINES,
    include_windows_events: bool = True,
    exception_text: str | None = None,
    output_path: str | Path | None = None,
):
    """Write a crash report inside the repository unless explicitly overridden.

    ``.log`` is intentional: the repository already ignores ``*.log``, so local
    crash evidence stays easy to find without ever becoming a Git change.
    """
    return write_crash_report(
        control,
        agent_log_lines=agent_log_lines,
        include_windows_events=include_windows_events,
        exception_text=exception_text,
        output_path=(output_path or default_repo_crash_report_path()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a paste-ready Balatro agent crash report under "
            "logs/balatro/crash-reports. The report is read-only and never sends "
            "a bridge/gameplay command."
        )
    )
    parser.add_argument("--control-dir")
    parser.add_argument("--lines", type=int, default=DEFAULT_AGENT_LOG_LINES)
    parser.add_argument("--output")
    parser.add_argument("--no-windows-events", action="store_true")
    args = parser.parse_args()

    if args.lines < 1:
        parser.error("--lines must be positive")

    control = BalatroAgentControl(args.control_dir)
    try:
        path, report = write_repo_crash_report(
            control,
            agent_log_lines=args.lines,
            include_windows_events=not args.no_windows_events,
            output_path=args.output,
        )
    except Exception as error:
        print("Balatro Agent crash report -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        return 2

    print(report, end="")
    print(f"Crash report saved -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
