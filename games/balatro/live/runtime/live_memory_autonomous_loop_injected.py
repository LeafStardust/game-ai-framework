from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter, sleep
from typing import Callable

from games.balatro.live.injected.bridge import InjectedBridgeError

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


def _terminal_stop_reason(snapshot) -> str | None:
    phase = str(snapshot.phase)
    # Balatro publishes G.GAME.won as soon as the Ante-8 final Boss is cleared,
    # while the public phase may still be ROUND_EVAL.  Waiting exclusively for
    # GAME_OVER lets END_ROUND cash out into Endless and permits more shop play.
    # The win bit is therefore the authoritative terminal signal for the target
    # run regardless of the transient post-hand phase.
    if bool(snapshot.payload.get("won")):
        return "game over (won)"
    if phase not in TERMINAL_PHASES:
        return None
    if phase == "GAME_OVER":
        outcome = "won" if bool(snapshot.payload.get("won")) else "lost"
        return f"game over ({outcome})"
    return f"terminal phase reached: {phase}"


class LiveMemoryInjectedAutonomousLoop:
    """Repeatedly replan from settled public Balatro checkpoints.

    The loop itself never submits a second action from an old recommendation.
    Every iteration calls the validated single-step runner again, so execution
    retains its exact stale-state checks, achievement guard, semantic dispatcher,
    and settled postcondition before another decision is even considered.

    ``STATE_COMPLETE`` alone is not sufficient to prove that every public number
    has stopped animating. Before planning a real action, production runners wait
    for two consecutive semantically equal public snapshots. If the state still
    changes after planning, that recommendation is discarded and replanned from
    the new authoritative checkpoint. Stale replans never consume a gameplay step.

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
        self.on_transition = on_transition

    def preview(self) -> AutonomousLoopStep:
        started = perf_counter()
        decision = self.runner.decide()
        elapsed = perf_counter() - started
        return self._step(1, decision, elapsed)

    def _wait_for_stable_checkpoint(self):
        """Wait read-only for two consecutive equal semantic snapshots.

        Test doubles and non-live runners may not expose an observer; in that case
        the existing runner-level stale guard remains the only authority.
        """
        observer = getattr(self.runner, "observer", None)
        if observer is None or not hasattr(observer, "observe"):
            return None

        deadline = perf_counter() + self.stability_timeout_seconds
        previous = observer.observe()
        while True:
            if perf_counter() >= deadline:
                raise AutonomousLoopGuardError(
                    "live public state did not become semantically stable before planning"
                )

            if self.stability_interval_seconds:
                sleep(self.stability_interval_seconds)
            current = observer.observe()

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

                terminal_reason = _terminal_stop_reason(decision.snapshot)
                if terminal_reason is not None:
                    return AutonomousLoopRun(tuple(completed), terminal_reason)

                if (
                    previous_after_sequence is not None
                    and decision.snapshot.sequence < previous_after_sequence
                ):
                    raise AutonomousLoopGuardError(
                        "observer checkpoint sequence regressed between autonomous steps"
                    )

                # An OFF request that arrives during a long planning call cancels
                # the recommendation before any gameplay command is submitted.
                if self.stop_requested():
                    return AutonomousLoopRun(tuple(completed), "stop requested")

                try:
                    result, status = self.runner.execute(decision)
                except AutonomousBridgeCapabilityError as error:
                    # No gameplay command was submitted. A stale installed bridge
                    # is an operational compatibility block, not a gameplay crash.
                    return AutonomousLoopRun(
                        tuple(completed),
                        f"bridge capability blocked: {error}",
                    )
                except AutonomousStepGuardError as error:
                    if "live state changed after autonomous planning" not in str(error):
                        raise

                    stale_replans += 1
                    if stale_replans <= self.stale_replan_limit:
                        # No gameplay command was submitted. Discard the old
                        # recommendation and restart this same gameplay step from
                        # a newly stabilized authoritative public checkpoint.
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
                        # The gameplay action already happened. Stop immediately so
                        # subsequent autonomous actions do not proceed without the
                        # requested durable telemetry.
                        return AutonomousLoopRun(
                            tuple(completed),
                            f"transition hook failed after executed action: {error}",
                        )

                terminal_reason = _terminal_stop_reason(after)
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
