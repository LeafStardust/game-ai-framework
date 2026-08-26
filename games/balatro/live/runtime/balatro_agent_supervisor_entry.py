from __future__ import annotations

import argparse
import traceback
from dataclasses import replace
from time import sleep

from games.balatro.actions import END_ROUND
from games.balatro.build_health_diagnostics import build_health_diagnostics_payload
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


CASH_OUT_DWELL_SECONDS = 1.50


def _is_recovered_stale_replan(error: BaseException) -> bool:
    return (
        isinstance(error, AutonomousStepGuardError)
        and "live state changed after autonomous planning" in str(error)
    )


def _validated_supervisor_bridge() -> FirstPartyBalatroBridge:
    """Require the currently loaded in-process bridge to match supervisor features.

    Balatro loads the bridge Lua from the fused executable only when the game starts.
    Updating the repository while Balatro is already running therefore leaves the
    process on the older bridge until Balatro is fully restarted. Require both
    unlock draining and the GAME_OVER pause-release repair before the autonomous
    loop is allowed to issue any gameplay action.
    """
    bridge = FirstPartyBalatroBridge(
        timeout=DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
    )
    status = bridge.status()
    if status.get("restart_unlock_drain") != "1":
        revision = status.get("bridge_revision", "unknown")
        raise RuntimeError(
            "loaded Balatro bridge is stale "
            f"(revision={revision}); this process does not contain required pack-state "
            "Joker-sale/restart support. Close Balatro completely, update/reinstall "
            "the repository bridge, then relaunch Balatro before starting the agent"
        )
    if status.get("restart_pause_release") != "1":
        revision = status.get("bridge_revision", "unknown")
        raise RuntimeError(
            "loaded Balatro bridge is stale "
            f"(revision={revision}); this process does not contain the GAME_OVER "
            "pause-release restart repair. Close Balatro completely, update/reinstall "
            "the repository bridge, then relaunch Balatro before starting the agent"
        )
    return bridge


def _diagnostic_runner_factory(
    observer,
    *,
    control: BalatroAgentControl,
    session_id: str,
    diagnostic_directory: str,
    unlock_campaign_config: UnlockCampaignConfig | None = None,
    collection_first: bool = False,
):
    runner = StrategyAwareLiveMemoryInjectedSingleStepRunner(
        observer,
        translator=FinisherAwareBalatroStateTranslator(),
        bridge=_validated_supervisor_bridge(),
        unlock_campaign_config=unlock_campaign_config,
        collection_first=collection_first,
    )
    original_decide = runner.decide
    original_execute = runner.execute

    def decide_with_build_health():
        decision = original_decide()
        diagnostics = dict(decision.decision_diagnostics or {})
        try:
            diagnostics["build_health"] = build_health_diagnostics_payload(
                decision.state,
            )
        except Exception as error:
            # Observability must never become an autonomous-gameplay failure mode.
            # The production decision layer still owns its own Build Health errors;
            # this guard is only for the post-decision telemetry attachment.
            diagnostics["build_health_error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
        return replace(decision, decision_diagnostics=diagnostics)

    def execute_with_diagnostics(decision):
        try:
            if str(getattr(decision.action, "name", "")) == END_ROUND:
                # END_ROUND is the cash-out click on the payout screen. Leave the
                # reward breakdown visible briefly before advancing so live users
                # can actually inspect the result. This is UI pacing only and does
                # not alter policy scoring, state interpretation or action choice.
                sleep(CASH_OUT_DWELL_SECONDS)
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

    runner.decide = decide_with_build_health
    runner.execute = execute_with_diagnostics
    return runner


def main() -> int:
    # Install the broad SHOP runtime contract only after ``games.balatro`` package
    # initialization has completed and this production entry point is executing.
    # Importing that graph from a package-level installer caused pytest/importlib to
    # observe a partially initialized ``games.balatro`` package and cascade collection
    # failures across otherwise unrelated Balatro tests.
    from games.balatro.shop_expectation_runtime_bound_policy import (
        install_shop_expectation_runtime_bounds,
    )

    install_shop_expectation_runtime_bounds()

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
        "--collection-first",
        action="store_true",
        help=(
            "make permanent profile discovery/unlock progress outrank ordinary "
            "strategy, economy and current-run win probability"
        ),
    )
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
            collection_first=args.collection_first,
        )

    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=DiscardHistorySupervisorLiveMemoryBalatroObserver,
        runner_factory=runner_factory,
        run_log_directory=args.run_log_directory,
        session_directory=args.session_directory,
        session_id=args.session_id,
        retry_losses=not args.no_retry_losses,
        collection_first=args.collection_first,
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
