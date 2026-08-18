from __future__ import annotations

import argparse
import traceback

from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.run_diagnostics import BalatroDiagnosticLogger
from games.balatro.unlock_campaign import (
    AUTO,
    SUPPORTED_JOKER_UNLOCK_TARGETS,
    UnlockCampaignConfig,
)

from .agent_control import BalatroAgentControl
from .balatro_agent_crash_report_repo import write_repo_crash_report
from .balatro_agent_supervisor import (
    DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
    BalatroAgentSupervisor,
)
from .finisher_state_translator import FinisherAwareBalatroStateTranslator
from .live_memory_autonomous_step_injected import AutonomousStepGuardError
from .live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
)
from .strategy_autonomous_runner import (
    StrategyAwareLiveMemoryInjectedSingleStepRunner,
)


def _is_recovered_stale_replan(error: BaseException) -> bool:
    return (
        isinstance(error, AutonomousStepGuardError)
        and "live state changed after autonomous planning" in str(error)
    )


def _diagnostic_runner_factory(
    observer,
    *,
    control: BalatroAgentControl,
    session_id: str,
    diagnostic_directory: str,
    unlock_campaign_config: UnlockCampaignConfig | None = None,
):
    runner = StrategyAwareLiveMemoryInjectedSingleStepRunner(
        observer,
        translator=FinisherAwareBalatroStateTranslator(),
        bridge=FirstPartyBalatroBridge(
            timeout=DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
        ),
        unlock_campaign_config=unlock_campaign_config,
    )
    original_execute = runner.execute

    def execute_with_diagnostics(decision):
        try:
            return original_execute(decision)
        except Exception as error:
            if _is_recovered_stale_replan(error):
                raise
            try:
                status = control.read_status()
                BalatroDiagnosticLogger(
                    session_id,
                    directory=diagnostic_directory,
                ).failure(
                    stage="execution_failure",
                    error=error,
                    status=status,
                    action=str(getattr(decision.action, "name", "")),
                    phase=str(decision.snapshot.phase),
                    checkpoint_sequence=int(decision.snapshot.sequence),
                )
            except Exception:
                pass
            raise

    runner.execute = execute_with_diagnostics
    return runner


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
    parser.add_argument("--diagnostic-directory", default="logs/balatro/diagnostics")
    parser.add_argument("--session-id")
    parser.add_argument("--no-retry-losses", action="store_true")
    parser.add_argument(
        "--unlock-joker",
        action="append",
        choices=(AUTO, *SUPPORTED_JOKER_UNLOCK_TARGETS),
        default=[],
        help=(
            "explicitly enable a default-off collection unlock campaign; repeat "
            "for multiple targets or use auto"
        ),
    )
    args = parser.parse_args()
    unlock_campaign_config = UnlockCampaignConfig.from_targets(args.unlock_joker)

    control = BalatroAgentControl(args.control_dir)
    supervisor: BalatroAgentSupervisor

    def runner_factory(observer):
        return _diagnostic_runner_factory(
            observer,
            control=control,
            session_id=supervisor.session_id,
            diagnostic_directory=args.diagnostic_directory,
            unlock_campaign_config=unlock_campaign_config,
        )

    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=DiscardHistorySupervisorLiveMemoryBalatroObserver,
        runner_factory=runner_factory,
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
        reason = f"supervisor failure: {error}"
        print("Balatro autonomous supervisor -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        print("Traceback ->")
        print(exception_text.rstrip())
        try:
            diagnostic = BalatroDiagnosticLogger(
                supervisor.session_id,
                directory=args.diagnostic_directory,
            )
            diagnostic.failure(
                stage="supervisor_failure",
                error=error,
                status=control.read_status(),
            )
            print(f"Diagnostic log -> {diagnostic.path}")
        except Exception as diagnostic_error:
            print(
                "Diagnostic log -> FAILED "
                f"({type(diagnostic_error).__name__}: {diagnostic_error})"
            )
        try:
            summary_path = supervisor._write_summary(
                won=False,
                stop_reason=reason,
            )
            print(f"Session summary -> {summary_path}")
        except Exception as summary_error:
            print(
                "Session summary -> FAILED "
                f"({type(summary_error).__name__}: {summary_error})"
            )
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
