from __future__ import annotations

import argparse
from pathlib import Path

from .hand_mouse import HAND_CONTROLS, HandMouseLayout
from .shop_mouse_calibration import WindowsCursorProvider, normalize_cursor
from .window import BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-hand-mouse.json"


def print_status(layout: HandMouseLayout) -> None:
    for control in ("play-hand", "discard"):
        try:
            point = layout.point_for(control)
        except RuntimeError:
            print(f"{control} -> no")
        else:
            print(f"{control} -> x={point.x:.6f} y={point.y:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record resolution-independent Balatro Play Hand / Discard button coordinates."
        )
    )
    parser.add_argument("controls", nargs="*", choices=sorted(HAND_CONTROLS))
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    if args.status and args.controls:
        parser.error("--status cannot be combined with calibration controls")
    if args.status and args.replace:
        parser.error("--status cannot be combined with --replace")
    if not args.status and not args.controls:
        parser.error("at least one hand control is required")

    try:
        if output.exists() and not args.replace:
            layout = HandMouseLayout.load(output)
        else:
            layout = HandMouseLayout()

        if args.status:
            print_status(layout)
            return 0

        locator = BalatroWindowLocator()
        cursor = WindowsCursorProvider()
        points = {
            "play-hand": layout.play_hand,
            "discard": layout.discard,
        }

        for control in args.controls:
            label = "Play Hand" if control == "play-hand" else "Discard"
            input(
                f"Move the cursor to the {label} button in Balatro, then press Enter here."
            )
            window = locator.find()
            point = normalize_cursor(window, cursor.position())
            points[control] = point
            print(
                f"Captured {control} -> x={point.x:.6f} y={point.y:.6f}"
            )

        layout = HandMouseLayout(
            play_hand=points["play-hand"],
            discard=points["discard"],
        )
        layout.save(output)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
