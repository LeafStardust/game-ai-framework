from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
    _semantic_payload,
)
from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class SemanticDifference:
    path: str
    before: object
    after: object


def _short(value: object, *, limit: int = 160) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def semantic_differences(
    before: Any,
    after: Any,
    *,
    path: str = "payload",
    limit: int = 20,
) -> tuple[SemanticDifference, ...]:
    """Return bounded leaf-level differences between public semantic payloads."""
    if limit < 1:
        raise ValueError("limit must be positive")

    result: list[SemanticDifference] = []

    def visit(left: Any, right: Any, current_path: str) -> None:
        if len(result) >= limit or left == right:
            return

        if isinstance(left, dict) and isinstance(right, dict):
            keys = sorted(set(left) | set(right), key=str)
            for key in keys:
                if len(result) >= limit:
                    break
                child_path = f"{current_path}.{key}"
                if key not in left:
                    result.append(SemanticDifference(child_path, "<missing>", right[key]))
                elif key not in right:
                    result.append(SemanticDifference(child_path, left[key], "<missing>"))
                else:
                    visit(left[key], right[key], child_path)
            return

        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            if len(left) != len(right):
                result.append(
                    SemanticDifference(
                        f"{current_path}.length",
                        len(left),
                        len(right),
                    )
                )
                if len(result) >= limit:
                    return
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                if len(result) >= limit:
                    break
                visit(left_item, right_item, f"{current_path}[{index}]")
            return

        result.append(SemanticDifference(current_path, left, right))

    visit(before, after, path)
    return tuple(result)


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(observer)
            decision = runner.decide()
            latest = observer.observe()

            before_payload = _semantic_payload(decision.snapshot.payload)
            after_payload = _semantic_payload(latest.payload)
            differences = list(
                semantic_differences(before_payload, after_payload, limit=20)
            )
            if decision.snapshot.phase != latest.phase:
                differences.insert(
                    0,
                    SemanticDifference(
                        "phase",
                        decision.snapshot.phase,
                        latest.phase,
                    ),
                )
            if decision.snapshot.state_complete != latest.state_complete:
                differences.insert(
                    0,
                    SemanticDifference(
                        "state_complete",
                        decision.snapshot.state_complete,
                        latest.state_complete,
                    ),
                )

            print("Live-memory autonomous stale diagnostic -> READY")
            print(f"Phase before -> {decision.snapshot.phase}")
            print(f"Sequence before -> {decision.snapshot.sequence}")
            print(f"Decision latency -> {runner.last_policy_seconds:.3f}s policy")
            print(f"Phase after -> {latest.phase}")
            print(f"Sequence after -> {latest.sequence}")
            print(f"Semantic differences -> {len(differences)}")
            for difference in differences[:20]:
                print(
                    f"  {difference.path}: "
                    f"{_short(difference.before)} -> {_short(difference.after)}"
                )
            if not differences:
                print("Result -> semantic gameplay state remained stable")
            else:
                print("Result -> semantic gameplay state changed during planning")
            print("Gameplay action executed -> False")
            print("Achievement status command sent -> False")
            print("Mouse input sent -> False")
            print("Observation process writes -> False")
            return 0
    except (RuntimeError, ValueError) as error:
        print("Live-memory autonomous stale diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Gameplay action executed -> False")
        print("Mouse input sent -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
