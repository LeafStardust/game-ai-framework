from __future__ import annotations

import argparse
import time

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_pack_selected_card_confirm_mouse import (
    LivePackSelectedCardConfirmError,
    LivePackSelectedCardConfirmExecutor,
    pack_contains_card,
)
from .mouse import BalatroMouseController


def _wait_for_confirm_result(observer, before, selected, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_phase = before.phase
    last_present = True
    while time.monotonic() < deadline:
        after = observer.observe()
        last_phase = after.phase
        last_present = pack_contains_card(observer, selected.address)
        if after.phase != before.phase:
            return after, last_present, "phase changed"
        if not last_present:
            return after, last_present, "selected card consumed from pack"
        time.sleep(0.05)
    raise TimeoutError(
        "timed out verifying pack confirm: "
        f"phase={last_phase}, selected_card_present={last_present}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or confirm exactly one already-highlighted pack card. The executor "
            "derives the exact use_card/can_select_card control from live memory, "
            "live-verifies its geometry, searches locally around that memory guess if "
            "needed, and only then falls back to a whole-client search."
        )
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            executor = LivePackSelectedCardConfirmExecutor(
                observer=observer,
                mouse=mouse,
            )
            snapshot, selected = executor.preview()

            print("Live pack selected-card confirm validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Highlighted card address -> 0x{selected.address:x}")

            if not args.execute:
                print("Mouse movement sent -> False")
                print("Mouse clicks sent -> False")
                print(
                    "Re-run with --execute to locate live use_card/can_select_card "
                    "and send exactly one confirm click."
                )
                return 0

            before, selected, target = executor.dispatch()
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print("Clicks sent -> 1")
            print(f"Confirm node address -> 0x{target.node_address:x}")
            print(f"Confirm button -> {target.button!r}")
            print(f"Confirm func -> {target.func!r}")
            print(f"Confirm id -> {target.control_id!r}")
            print(
                "Verified live confirm point -> "
                f"x={target.screen_point.x} y={target.screen_point.y}"
            )
            print(f"Verified confirm hit signal -> {target.hit_signal}")
            print(f"Confirm location source -> {target.location_source}")
            print(f"Memory confirm candidates -> {target.memory_candidates}")
            print(f"Local memory search used -> {target.used_local_search}")
            print(f"Fallback screen search used -> {target.used_fallback_search}")
            print(f"Confirm hover probes required -> {target.probes}")
            print("Waiting for live pack-confirm postcondition")

            after, still_present, reason = _wait_for_confirm_result(
                observer, before, selected
            )
    except (OSError, RuntimeError, TimeoutError, ValueError, LivePackSelectedCardConfirmError) as error:
        print("Live pack selected-card confirm validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Selected card still in G.pack_cards -> {still_present}")
    print(f"Postcondition -> {reason}")
    print("Live pack selected-card confirm checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
