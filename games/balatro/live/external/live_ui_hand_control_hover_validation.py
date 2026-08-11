from __future__ import annotations

import argparse
import time

from .live_memory_hand_executor import resolve_live_hand_controls
from .live_memory_observer import LiveMemoryBalatroObserver, _number
from .live_ui_hover_validation import (
    _active_hover_truths,
    _differences,
    _flatten_state,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Move the normal cursor to the live-memory-derived Play Hand or Discard "
            "button and verify Balatro marks that exact UI element as hovered. No click."
        )
    )
    parser.add_argument("--control", choices=("play", "discard"), default="play")
    parser.add_argument("--settle", type=float, default=0.30)
    args = parser.parse_args()
    if args.settle < 0:
        parser.error("--settle cannot be negative")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            controls = resolve_live_hand_controls(decoder, root)
            target = controls.play if args.control == "play" else controls.discard
            other = controls.discard if args.control == "play" else controls.play

            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None:
                raise RuntimeError("Balatro logical TILE_W/TILE_H are unavailable")

            before_target = _flatten_state(decoder, target.address)
            before_other = _flatten_state(decoder, other.address)

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            point = transform.card_center(target.geometry)
            mouse.move_screen(point)
            if args.settle:
                time.sleep(args.settle)

            # Re-resolve in case the UIBox rebuilt during focus/hover.
            decoder, _, root = observer._root()
            controls_after = resolve_live_hand_controls(decoder, root)
            target_after = controls_after.play if args.control == "play" else controls_after.discard
            other_after = controls_after.discard if args.control == "play" else controls_after.play
            after_target = _flatten_state(decoder, target_after.address)
            after_other = _flatten_state(decoder, other_after.address)
    except Exception as error:
        print("Live hand control hover validation -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        return 2

    target_changes = _differences(before_target, after_target)
    other_changes = _differences(before_other, after_other)
    target_hover = _active_hover_truths(after_target)
    other_hover = _active_hover_truths(after_other)

    print("Live hand control hover validation -> DIAGNOSTIC")
    print("Observation source -> live Balatro process memory")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print(
        f"Target control -> {args.control.upper()} "
        f"id={target.ui_id!r} func={target.callback!r}"
    )
    print(f"Computed screen center -> ({point.x},{point.y})")
    for key, (old, new) in target_changes.items():
        print(f"  target {key}: {old!r} -> {new!r}")
    for key, (old, new) in other_changes.items():
        if "hover" in key.casefold() or "collide" in key.casefold():
            print(f"  other {key}: {old!r} -> {new!r}")

    if target_hover and not other_hover:
        print("Hovered-control identity -> PASS")
        print("Target hover field(s) -> " + ", ".join(target_hover))
        print("Live hand control coordinate validation -> PASS")
        return 0

    print("Hovered-control identity -> INCONCLUSIVE")
    print(
        "Target active hover fields -> "
        + (", ".join(target_hover) if target_hover else "none")
    )
    print(
        "Other active hover fields -> "
        + (", ".join(other_hover) if other_hover else "none")
    )
    print("Live hand control coordinate validation -> NOT_YET_VALIDATED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
