from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter

from games.balatro.live.injected.bridge import InjectedBridgeError

from .live_memory_autonomous_stale_diagnostic import semantic_differences
from .live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    AutonomousStepGuardError,
    LiveMemoryInjectedSingleStepRunner,
    UnsupportedAutonomousPhase,
    _action_text,
    _semantic_payload,
)
from .live_memory_observer import LiveMemoryBalatroObserver


class AutonomousLoopGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class AutonomousLoopStep:
    number: int
    decision: AutonomousStepDecision
    decision_seconds: float
    observation_seconds: float
    translation_seconds: float
    policy_seconds: float
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


class LiveMemoryInjectedAutonomousLoop:
    """Repeatedly replan from settled public Balatro checkpoints.

    The loop itself never submits a second action from an old recommendation.
    Every iteration calls the validated single-step runner again, so execution
    retains its exact stale-state checks, achievement guard, semantic dispatcher,
    and settled postcondition before another decision is even considered.
    """

    def __init__(self, runner: LiveMemoryInjectedSingleStepRunner, *, max_steps: int):
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.runner = runner
        self.max_steps = int(max_steps)

    def preview(self) -> AutonomousLoopStep:
        started = perf_counter()
        decision = self.runner.decide()
        elapsed = perf_counter() - started
        return self._step(1, decision, elapsed)

    def execute(self, *, expected_start_phase: str) -> AutonomousLoopRun:
        if not expected_start_phase:
            raise ValueError("expected_start_phase is required")

        completed: list[AutonomousLoopStep] = []
        previous_after_sequence: int | None = None

        for number in range(1, self.max_steps + 1):
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

            if (
                previous_after_sequence is not None
                and decision.snapshot.sequence < previous_after_sequence
            ):
                raise AutonomousLoopGuardError(
                    "observer checkpoint sequence regressed between autonomous steps"
                )

            try:
                result, status = self.runner.execute(decision)
            except AutonomousStepGuardError as error:
                if "live state changed after autonomous planning" not in str(error):
                    raise
                latest = self.runner.observer.observe()
                details = _stale_difference_details(decision, latest)
                suffix = (
                    "; semantic differences: " + "; ".join(details)
                    if details
                    else "; semantic differences unavailable on follow-up snapshot"
                )
                raise AutonomousLoopGuardError(str(error) + suffix) from error

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
                    after_phase=str(after.phase),
                    after_sequence=int(after.sequence),
                    achievement_gate=status.get("achievement_gate"),
                )
            )
            previous_after_sequence = int(after.sequence)

        return AutonomousLoopRun(tuple(completed), "max steps reached")

    def _step(
        self,
        number: int,
        decision: AutonomousStepDecision,
        decision_seconds: float,
        *,
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
                "Execution semantics -> one action, settled checkpoint, fresh "
                "observation, fresh decision"
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
