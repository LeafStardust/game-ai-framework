from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.run_experience_transition import log_successful_live_transition

from .balatro_agent_supervisor import (
    DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
    wait_for_stable_startup_snapshot,
)
from .finisher_state_translator import FinisherAwareBalatroStateTranslator
from .live_memory_autonomous_loop_injected import LiveMemoryInjectedAutonomousLoop
from .live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
)
from .playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)


D13_SOURCE = "D13 contextual blind play-vs-skip policy"
D13_SKIP_ACTION = "SKIP_BLIND"
DEFAULT_STOP_BEFORE_ANTE = 5
DEFAULT_MAX_STEPS = 100


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _payload(snapshot) -> dict[str, Any]:
    value = getattr(snapshot, "payload", None)
    return value if isinstance(value, dict) else {}


def _ante(snapshot) -> int:
    payload = _payload(snapshot)
    value = payload.get("ante_num", payload.get("ante", 0))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _is_d13_skip(decision) -> bool:
    action = getattr(getattr(decision, "action", None), "name", "")
    return (
        str(getattr(decision, "source", "")) == D13_SOURCE
        and str(action) == D13_SKIP_ACTION
        and str(getattr(getattr(decision, "snapshot", None), "phase", ""))
        == "BLIND_SELECT"
    )


@dataclass
class D13ValidationState:
    stop_before_ante: int = DEFAULT_STOP_BEFORE_ANTE
    transition_count: int = 0
    stop: bool = False
    ante_limit_reached: bool = False
    skip_evidence: dict[str, Any] | None = None

    def stop_requested(self) -> bool:
        return bool(self.stop)

    def capture(self, decision, result) -> None:
        self.transition_count += 1
        after = result.after

        if _is_d13_skip(decision):
            before_payload = _payload(decision.snapshot)
            blind = (
                before_payload.get("blind")
                if isinstance(before_payload.get("blind"), dict)
                else {}
            )
            self.skip_evidence = {
                "ante": _ante(decision.snapshot),
                "blind_type": str(blind.get("type") or "UNKNOWN").upper(),
                "tag_key": blind.get("tag"),
                "action": D13_SKIP_ACTION,
                "decision_source": D13_SOURCE,
                "notes": [str(note) for note in getattr(decision, "notes", ())],
                "diagnostics": _sanitize(
                    getattr(decision, "decision_diagnostics", {}) or {}
                ),
                "checkpoint_sequence_before": int(decision.snapshot.sequence),
                "checkpoint_sequence_after": int(after.sequence),
                "phase_after": str(after.phase),
            }
            self.stop = True
            return

        after_ante = _ante(after)
        if after_ante >= int(self.stop_before_ante):
            self.ante_limit_reached = True
            self.stop = True


def run_d13_agent_validation(
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    stop_before_ante: int = DEFAULT_STOP_BEFORE_ANTE,
    run_log_directory: str | Path = "logs/balatro/runs",
) -> dict[str, Any]:
    if not 1 <= int(max_steps) <= 100:
        raise ValueError("max_steps must be between 1 and 100")
    if not 2 <= int(stop_before_ante) <= 5:
        raise ValueError("stop_before_ante must be between 2 and 5")

    run_id = f"d13-validation-{uuid.uuid4().hex[:12]}"
    validation = D13ValidationState(stop_before_ante=int(stop_before_ante))

    with DiscardHistorySupervisorLiveMemoryBalatroObserver() as observer:
        initial = wait_for_stable_startup_snapshot(observer)
        initial_payload = _payload(initial)
        deck = str(initial_payload.get("deck") or "").upper()
        stake = str(initial_payload.get("stake") or "").upper()
        start_ante = _ante(initial)

        if (deck, stake) != ("RED", "WHITE"):
            raise RuntimeError(
                f"D13 validation requires RED/WHITE; observed {deck or 'UNKNOWN'}/"
                f"{stake or 'UNKNOWN'}"
            )
        if start_ante >= int(stop_before_ante):
            raise RuntimeError(
                f"D13 validation must start before Ante {stop_before_ante}; "
                f"observed Ante {start_ante}"
            )

        runner = PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
            observer,
            translator=FinisherAwareBalatroStateTranslator(),
            bridge=FirstPartyBalatroBridge(
                timeout=DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
            ),
        )

        def on_transition(decision, result, status):
            log_successful_live_transition(
                decision,
                result,
                run_id=run_id,
                directory=run_log_directory,
            )
            validation.capture(decision, result)

        loop = LiveMemoryInjectedAutonomousLoop(
            runner,
            max_steps=int(max_steps),
            stop_requested=validation.stop_requested,
            on_transition=on_transition,
        )
        run = loop.execute(expected_start_phase=str(initial.phase))

    if validation.skip_evidence is not None:
        status = "SKIP_VALIDATED"
    elif validation.ante_limit_reached:
        status = "NO_SKIP_BEFORE_ANTE_LIMIT"
    elif run.stop_reason.startswith("game over"):
        status = "TERMINAL_BEFORE_SKIP"
    elif run.stop_reason == "max steps reached":
        status = "MAX_STEPS_BEFORE_SKIP"
    else:
        status = "STOPPED_BEFORE_SKIP"

    return {
        "mode": "BOUNDED_D13_AGENT_VALIDATION",
        "status": status,
        "run_id": run_id,
        "deck": deck,
        "stake": stake,
        "start_ante": start_ante,
        "start_phase": str(initial.phase),
        "stop_before_ante": int(stop_before_ante),
        "max_steps": int(max_steps),
        "gameplay_actions_executed": len(run.steps),
        "loop_stop_reason": str(run.stop_reason),
        "skip_validated": validation.skip_evidence is not None,
        "skip_evidence": validation.skip_evidence,
        "authoritative_log": str(Path(run_log_directory) / f"{run_id}.jsonl"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the production Red/White agent only long enough to validate one "
            "real D13 blind skip. The run stops immediately after the first "
            "executed SKIP_BLIND, before Ante 5, or at the hard action cap."
        )
    )
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--stop-before-ante",
        type=int,
        default=DEFAULT_STOP_BEFORE_ANTE,
    )
    parser.add_argument("--run-log-directory", default="logs/balatro/runs")
    args = parser.parse_args()

    try:
        result = run_d13_agent_validation(
            max_steps=args.max_steps,
            stop_before_ante=args.stop_before_ante,
            run_log_directory=args.run_log_directory,
        )
    except Exception as error:
        print("D13 bounded agent validation -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "SKIP_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
