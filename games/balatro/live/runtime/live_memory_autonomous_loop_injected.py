from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter, sleep
from typing import Callable

from games.balatro.live.injected.bridge import InjectedBridgeError
from games.balatro.live.injected.hand_dispatcher import (
    InjectedHandActionPostconditionError,
)

from .live_memory_autonomous_stale_diagnostic import semantic_differences
from .live_memory_autonomous_step_injected import (
    AutonomousBridgeCapabilityError,
    AutonomousStepDecision,
    AutonomousStepGuardError,
    LiveMemoryInjectedSingleStepRunner,
    UnsupportedAutonomousPhase,
    _action_text,
    _same_snapshot,
    _semantic_payload,
)
from .live_memory_observer import LiveMemoryBalatroObserver


class AutonomousLoopGuardError(RuntimeError):
    pass


TERMINAL_PHASES = frozenset({"GAME_OVER"})


@dataclass(frozen=True)
class AutonomousLoopStep:
    number: int
    decision: AutonomousStepDecision
    decision_seconds: float
    observation_seconds: float
    translation_seconds: float
    policy_seconds: float
    stale_replans: int = 0
    after_phase: str | None = None
    after_sequence: int | None = None
    achievement_gate: str | None = None


@dataclass(frozen=True)
class AutonomousLoopRun:
    steps: tuple[AutonomousLoopStep, ...]
    stop_reason: str


def _short_stale_value(value: object, *, limit: int = 80) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _stale_difference_details(
    decision: AutonomousStepDecision,
    latest,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    details: list[str] = []
    if decision.snapshot.phase != latest.phase:
        details.append(
            f"phase: {decision.snapshot.phase!r} -> {latest.phase!r}"
        )
    if decision.snapshot.state_complete != latest.state_complete:
        details.append(
            "state_complete: "
            f"{decision.snapshot.state_complete!r} -> {latest.state_complete!r}"
        )

    remaining = max(0, limit - len(details))
    if remaining:
        differences = semantic_differences(
            _semantic_payload(decision.snapshot.payload),
            _semantic_payload(latest.payload),
            limit=remaining,
        )
        details.extend(
            f"{difference.path}: "
            f"{_short_stale_value(difference.before)} -> "
            f"{_short_stale_value(difference.after)}"
            for difference in differences
        )
    return tuple(details[:limit])


def _terminal_stop_reason(
    snapshot,
    *,
    resume_won_run: bool = False,
) -> str | None:
    phase = str(snapshot.phase)

    # Balatro's public ``won`` bit persists after the run has been won and, on a
    # later failed Endless/final-blind GAME_OVER frame, may still be true. A
    # GAME_OVER checkpoint is therefore authoritative loss evidence and must not be
    # reclassified by that sticky profile/run flag. Ordinary wins are observed on
    # the pre-GAME_OVER won checkpoint (for example ROUND_EVAL), where the bit is
    # safe to use and the supervisor auto-stops before a later game-over frame.
    if phase == "GAME_OVER":
        return "game over (lost)"

    if bool(snapshot.payload.get("won")) and not resume_won_run:
        return "game over (won)"
    if phase not in TERMINAL_PHASES:
        return None
    return f"terminal phase reached: {phase}"


class LiveMemoryInjectedAutonomousLoop:
    """Repeatedly replan from settled public Balatro checkpoints.

    The loop itself never submits a second action from an old recommendation.
    Every iteration calls the validated single-step runner again, so execution
    retains its exact stale-state checks, achievement guard, semantic dispatcher,
    and settled postcondition before another decision is even considered.

    ``STATE_COMPLETE`` alone is not sufficient to prove that every public number
    has stopped animating. Before planning a real action, production runners prefer
    two consecutive semantically equal public snapshots. Some native Balatro
    transitions (notably booster-pack opening/reveal animations) can keep changing
    legitimate public fields for longer than the nominal stability window while
    still reporting a complete actionable state. In that case the stability timeout
    is a soft boundary: planning may proceed from the newest complete snapshot and
    the runner's mandatory pre-execution stale-state guard remains authoritative.
    An incomplete snapshot at timeout still fails closed.

    ``max_steps=None`` means run until a terminal/unsupported/safe-stop condition.
    A stop request is checked before planning and again immediately before action
    submission, so turning the agent off never deliberately starts another action.
    The optional transition hook runs only after an action has reached its settled
    authoritative postcondition.
    """

    DEFAULT_STALE_REPLAN_LIMIT = 3
    DEFAULT_STABILITY_INTERVAL_SECONDS = 0.10
    DEFAULT_STABILITY_TIMEOUT_SECONDS = 2.0

    def __init__(
        self,
        runner: LiveMemoryInjectedSingleStepRunner,
        *,
        max_steps: int | None,
        stale_replan_limit: int = DEFAULT_STALE_REPLAN_LIMIT,
        stability_interval_seconds: float = DEFAULT_STABILITY_INTERVAL_SECONDS,
        stability_timeout_seconds: float = DEFAULT_STABILITY_TIMEOUT_SECONDS,
        stop_requested: Callable[[], bool] | None = None,
        resume_won_run: bool = False,
        on_transition: Callable[[AutonomousStepDecision, object, dict[str, str]], None]
        | None = None,
    ):
        if max_steps is not None and max_steps < 1:
            raise ValueError("max_steps must be positive when bounded")
        if stale_replan_limit < 0:
            raise ValueError("stale_replan_limit cannot be negative")
        if stability_interval_seconds < 0:
            raise ValueError("stability_interval_seconds cannot be negative")
        if stability_timeout_seconds <= 0:
            raise ValueError("stability_timeout_seconds must be positive")
        self.runner = runner
        self.max_steps = int(max_steps) if max_steps is not None else None
        self.stale_replan_limit = int(stale_replan_limit)
        self.stability_interval_seconds = float(stability_interval_seconds)
        self.stability_timeout_seconds = float(stability_timeout_seconds)
        self.stop_requested = stop_requested or (lambda: False)
        self.resume_won_run = bool(resume_won_run)
        self.on_transition = on_transition

    def preview(self) -> AutonomousLoopStep:
        started = perf_counter()
        decision = self.runner.decide()
        elapsed = perf_counter() - started
        return self._step(1, decision, elapsed)

    def _wait_for_stable_checkpoint(self):
        """Prefer a stable checkpoint, but do not crash on complete animation churn.

        A two-snapshot semantic match is the preferred planning boundary. If the
        timeout expires while Balatro still exposes a complete public snapshot,
        return that newest checkpoint and let the runner's final stale-state check
        decide whether execution is still safe. This prevents long native pack/UI
        animations from being misclassified as fatal instability without weakening
        the action-submission guard. Incomplete state continues to fail closed.
        """
        observer = getattr(self.runner, "observer", None)
        if observer is None or not hasattr(observer, "observe"):
            return None

        deadline = perf_counter() + self.stability_timeout_seconds
        previous = observer.observe()
        latest_complete = previous if previous.state_complete else None
        while True:
            if perf_counter() >= deadline:
                if latest_complete is not None:
                    return latest_complete
                raise AutonomousLoopGuardError(
                    "live public state remained incomplete before planning"
                )

            if self.stability_interval_seconds:
                sleep(self.stability_interval_seconds)
            current = observer.observe()
            if current.state_complete:
                latest_complete = current

            if (
                previous.state_complete
                and current.state_complete
                and _same_snapshot(previous, current)
            ):
                return current
            previous = current

    def execute(self, *, expected_start_phase: str) -> AutonomousLoopRun:
        if not expected_start_phase:
            raise ValueError("expected_start_phase is required")

        completed: list[AutonomousLoopStep] = []
        previous_after_sequence: int | None = None
        number = 1

        while self.max_steps is None or number <= self.max_steps:
            if self.stop_requested():
                return AutonomousLoopRun(tuple(completed), "stop requested")

            stale_replans = 0

            while True:
                if self.stop_requested():
                    return AutonomousLoopRun(tuple(completed), "stop requested")

                self._wait_for_stable_checkpoint()

                if self.stop_requested():
                    return AutonomousLoopRun(tuple(completed), "stop requested")

                started = perf_counter()
                try:
                    decision = self.runner.decide()
                except UnsupportedAutonomousPhase as error:
                    return AutonomousLoopRun(
                        tuple(completed),
                        f"unsupported phase: {error}",
                    )
                elapsed = perf_counter() - started

                if number == 1 and decision.snapshot.phase != expected_start_phase:
                    raise AutonomousLoopGuardError(
                        f"expected start phase {expected_start_phase}, "
                        f"observed {decision.snapshot.phase}"
                    )

                terminal_reason = _terminal_stop_reason(
                    decision.snapshot,
                    resume_won_run=self.resume_won_run,
                )
                if terminal_reason is not None:
                    return AutonomousLoopRun(tuple(completed), terminal_reason)

                if (
                    previous_after_sequence is not None
                    and decision.snapshot.sequence < previous_after_sequence
                ):
                    raise AutonomousLoopGuardError(
                        "observer checkpoint sequence regressed between autonomous steps"
                    )

                if self.stop_requested():
                    return AutonomousLoopRun(tuple(completed), "stop requested")

                try:
                    result, status = self.runner.execute(decision)
                except AutonomousBridgeCapabilityError as error:
                    return AutonomousLoopRun(
                        tuple(completed),
                        f"bridge capability blocked: {error}",
                    )
                except AutonomousStepGuardError as error:
                    if "live state changed after autonomous planning" not in str(error):
                        raise

                    stale_replans += 1
                    if stale_replans <= self.stale_replan_limit:
                        continue

                    latest = self.runner.observer.observe()
                    details = _stale_difference_details(decision, latest)
                    suffix = (
                        "; semantic differences: " + "; ".join(details)
                        if details
                        else "; semantic differences unavailable on follow-up snapshot"
                    )
                    raise AutonomousLoopGuardError(
                        "stale-state replan limit exceeded after "
                        f"{stale_replans} attempts; {error}{suffix}"
                    ) from error
                except InjectedHandActionPostconditionError as error:
                    # A held consumable may be accepted by Balatro's native callback
                    # while the engine is still in a transient UI/action lock, then
                    # never actually consume or mutate its intended target. The
                    # dispatcher correctly refuses to claim success. Quarantine that
                    # exact live consumable and replan from fresh public state instead
                    # of crashing or retrying the same no-op forever.
                    if "timed out verifying injected consumable use" not in str(error):
                        raise
                    quarantine = getattr(
                        self.runner,
                        "quarantine_failed_consumable",
                        None,
                    )
                    if not callable(quarantine) or not quarantine(decision):
                        raise
                    stale_replans += 1
                    continue
                except InjectedBridgeError as error:
                    if "action requires " not in str(error):
                        raise
                    observer = getattr(self.runner, "observer", None)
                    if observer is None or not hasattr(observer, "observe"):
                        raise
                    latest = observer.observe()
                    if _same_snapshot(decision.snapshot, latest):
                        raise

                    stale_replans += 1
                    if stale_replans <= self.stale_replan_limit:
                        continue

                    details = _stale_difference_details(decision, latest)
                    suffix = (
                        "; semantic differences: " + "; ".join(details)
                        if details
                        else "; semantic differences unavailable on follow-up snapshot"
                    )
                    raise AutonomousLoopGuardError(
                        "stale-state replan limit exceeded after bridge phase race "
                        f"({stale_replans} attempts); {error}{suffix}"
                    ) from error

                after = result.after
                if after.sequence <= decision.snapshot.sequence:
                    raise AutonomousLoopGuardError(
                        "gameplay action did not advance the authoritative public checkpoint"
                    )

                completed.append(
                    self._step(
                        number,
                        decision,
                        elapsed,
                        stale_replans=stale_replans,
                        after_phase=str(after.phase),
                        after_sequence=int(after.sequence),
                        achievement_gate=status.get("achievement_gate"),
                    )
                )
                previous_after_sequence = int(after.sequence)

                if self.on_transition is not None:
                    try:
                        self.on_transition(decision, result, status)
                    except Exception as error:
                        return AutonomousLoopRun(
                            tuple(completed),
                            f"transition hook failed after executed action: {error}",
                        )

                terminal_reason = _terminal_stop_reason(
                    after,
                    resume_won_run=self.resume_won_run,
                )
                if terminal_reason is not None:
                    return AutonomousLoopRun(tuple(completed), terminal_reason)

                if self.stop_requested():
                    return AutonomousLoopRun(tuple(completed), "stop requested")
                break

            number += 1

        return AutonomousLoopRun(tuple(completed), "max steps reached")

    def _step(
        self,
        number: int,
        decision: AutonomousStepDecision,
        decision_seconds: float,
        *,
        stale_replans: int = 0,
        after_phase: str | None = None,
        after_sequence: int | None = None,
        achievement_gate: str | None = None,
    ) -> AutonomousLoopStep:
        return AutonomousLoopStep(
            number=number,
            decision=decision,
            decision_seconds=float(decision_seconds),
            observation_seconds=float(self.runner.last_observation_seconds),
            translation_seconds=float(self.runner.last_translation_seconds),
            policy_seconds=float(self.runner.last_policy_seconds),
            stale_replans=int(stale_replans),
            after_phase=after_phase,
            after_sequence=after_sequence,
            achievement_gate=achievement_gate,
        )


def _print_step(step: AutonomousLoopStep, *, executed: bool) -> None:
    decision = step.decision
    print(f"Step {step.number} -> {_action_text(decision)}")
    print(f"  phase_before={decision.snapshot.phase}")
    print(f"  decision_source={decision.source}")
    print(f"  decision_seconds={step.decision_seconds:.3f}")
    print(f"  observation_seconds={step.observation_seconds:.3f}")
    print(f"  translation_seconds={step.translation_seconds:.3f}")
    print(f"  policy_seconds={step.policy_seconds:.3f}")
    print(f"  stale_replans={step.stale_replans}")
    for note in decision.notes:
        print(f"  {note}")
    if executed:
        print(f"  achievement_gate={step.achievement_gate or 'MISSING'}")
        print(f"  checkpoint_sequence={step.after_sequence}")
        print(f"  phase_after={step.after_phase}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Persist one live Balatro observer/bridge session and repeatedly choose "
            "exactly one action from each newly settled public checkpoint. Preview "
            "is read-only. Execution never chains a precomputed action sequence."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--max-steps",
        type=int,
        help="required with --execute; hard cap on real gameplay actions",
    )
    parser.add_argument(
        "--expect-start-phase",
        help="required with --execute; blocks if the first observed phase differs",
    )
    parser.add_argument("--max-horizon", type=int)
    parser.add_argument("--max-search-nodes", type=int)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    args = parser.parse_args()

    if args.execute:
        if args.max_steps is None:
            parser.error("--execute requires --max-steps")
        if args.expect_start_phase is None:
            parser.error("--execute requires --expect-start-phase")
    else:
        if args.max_steps is not None:
            parser.error("--max-steps is only valid with --execute")
        if args.expect_start_phase is not None:
            parser.error("--expect-start-phase is only valid with --execute")

    if args.max_steps is not None and not 1 <= args.max_steps <= 100:
        parser.error("--max-steps must be between 1 and 100")
    for name in ("max_horizon", "max_search_nodes"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.exact_limit < 1 or args.child_exact_limit < 1:
        parser.error("exact combination limits must be positive")

    try:
        with LiveMemoryBalatroObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(
                observer,
                max_horizon=args.max_horizon,
                max_search_nodes=args.max_search_nodes,
                exact_limit=args.exact_limit,
                child_exact_limit=args.child_exact_limit,
            )
            loop = LiveMemoryInjectedAutonomousLoop(
                runner,
                max_steps=(args.max_steps if args.max_steps is not None else 1),
            )

            print("Live-memory autonomous injected loop -> READY")
            print("Observation source -> live Balatro process memory")
            print("Execution backend -> game-ai-framework injected Lua bridge")
            print("Persistent observer session -> True")
            print("Fresh decision after every settled checkpoint -> True")
            print("Pre-plan semantic stability check -> True")
            print(f"Stale-state replan limit -> {loop.stale_replan_limit}")
            print("Hidden action queue -> False")
            print("Hidden RNG/deck traversal -> False")
            print("Mouse fallback -> False")

            if not args.execute:
                step = loop.preview()
                _print_step(step, executed=False)
                print("Execution guard -> PREVIEW ONLY")
                print("Gameplay actions executed -> 0")
                print("Achievement status command sent -> False")
                return 0

            assert args.max_steps is not None
            assert args.expect_start_phase is not None
            print(
                "WARNING -> --execute is armed: the loop may invoke up to "
                f"{args.max_steps} real in-process Balatro gameplay actions"
            )
            print(
                "Execution semantics -> stabilize, decide one action, settled "
                "checkpoint, fresh observation, fresh decision"
            )

            run = loop.execute(expected_start_phase=args.expect_start_phase)
            for step in run.steps:
                _print_step(step, executed=True)
            print(f"Gameplay actions executed -> {len(run.steps)}")
            print(f"Stop reason -> {run.stop_reason}")
            print("Mouse input sent -> False")
            return 0
    except AutonomousLoopGuardError as error:
        print("Live-memory autonomous injected loop -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 0
    except AutonomousStepGuardError as error:
        print("Live-memory autonomous injected loop -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 0
    except UnsupportedAutonomousPhase as error:
        print("Live-memory autonomous injected loop -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 0
    except InjectedBridgeError as error:
        print("Live-memory autonomous injected loop -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2
    except (RuntimeError, ValueError) as error:
        print("Live-memory autonomous injected loop -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
