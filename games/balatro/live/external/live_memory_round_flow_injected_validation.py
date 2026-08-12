from __future__ import annotations

import argparse

from games.balatro.actions import END_ROUND, END_SHOP, BalatroAction
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedActionDispatcher,
)

from .live_memory_observer import LiveMemoryBalatroObserver


_ACTION_BY_PHASE = {
    "ROUND_EVAL": END_ROUND,
    "SHOP": END_SHOP,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Guarded first-party injected validation for deterministic Balatro "
            "round flow. Preview mode is read-only. --execute invokes exactly "
            "one Cash Out or Next Round action and sends no mouse input."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-phase", choices=tuple(_ACTION_BY_PHASE))
    parser.add_argument("--expect-action", choices=tuple(_ACTION_BY_PHASE.values()))
    args = parser.parse_args()

    if args.execute and (
        args.expect_phase is None or args.expect_action is None
    ):
        parser.error(
            "--execute requires --expect-phase and --expect-action"
        )
    if not args.execute and (
        args.expect_phase is not None or args.expect_action is not None
    ):
        parser.error(
            "execution expectations are only valid with --execute"
        )

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        action_name = _ACTION_BY_PHASE.get(snapshot.phase)
        if action_name is None:
            parser.error(
                "round-flow injected validation requires ROUND_EVAL or SHOP, "
                f"observed {snapshot.phase}"
            )
        if not snapshot.state_complete:
            parser.error(
                f"{snapshot.phase} is not yet complete; wait for the UI to settle"
            )

        print("Live-memory first-party injected round flow -> READY")
        print("Observation source -> live Balatro process memory")
        print("Execution backend -> game-ai-framework injected Lua bridge")
        print("Runtime loader -> none (fused LÖVE archive)")
        print("Lovely required -> False")
        print("Steamodded required -> False")
        print("BalatroBot required -> False")
        print("Mouse calibration required -> False")
        print(f"Phase -> {snapshot.phase}")
        print(f"Recommended deterministic action -> {action_name}")
        print("Observation process writes -> False")

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        if args.expect_phase != snapshot.phase:
            print("Execution guard -> BLOCKED")
            print(
                f"Reason -> expected phase {args.expect_phase}, observed {snapshot.phase}"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0
        if args.expect_action != action_name:
            print("Execution guard -> BLOCKED")
            print(
                f"Reason -> expected action {args.expect_action}, current phase requires {action_name}"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest = observer.observe()
        if (
            latest.sequence != snapshot.sequence
            or latest.phase != snapshot.phase
            or not latest.state_complete
        ):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> live state changed before dispatch; re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> injected bridge unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        print("Execution guard -> PASS")
        print(
            "WARNING -> --execute is armed: one real in-process Balatro "
            "round-flow action will now be invoked"
        )
        print("Execution scope -> exactly one Cash Out or Next Round action")
        print("Mouse input sent -> False")

        try:
            result = LiveMemoryInjectedActionDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(
                BalatroAction(action_name),
                snapshot=latest,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            return 1

        print("Injected bridge command sent -> True")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {result.after.phase}")
        print(f"Money after -> {result.after.payload.get('money')}")
        print("Follow-up action executed -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
