from __future__ import annotations

import argparse
from pathlib import Path

from .blind_mouse import BLIND_CONTROLS, BlindMouseLayout
from .shop_mouse_calibration import WindowsCursorProvider, normalize_cursor
from .window import BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-blind-mouse.json"


def print_status(layout: BlindMouseLayout) -> None:
    for control in sorted(BLIND_CONTROLS):
        point = getattr(layout, control.replace("-", "_"))
        if point is None:
            print(f"{control} -> no")
        else:
            print(f"{control} -> x={point.x:.6f} y={point.y:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record resolution-independent Balatro blind Select/Skip coordinates."
        )
    )
    parser.add_argument("controls", nargs="*", choices=sorted(BLIND_CONTROLS))
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
        parser.error("at least one blind control is required")

    try:
        if output.exists() and not args.replace:
            layout = BlindMouseLayout.load(output)
        else:
            layout = BlindMouseLayout()

        if args.status:
            print_status(layout)
            return 0

        locator = BalatroWindowLocator()
        cursor = WindowsCursorProvider()
        points = {
            control: getattr(layout, control.replace("-", "_"))
            for control in BLIND_CONTROLS
        }

        for control in args.controls:
            blind, operation = control.split("-", 1)
            input(
                f"Move the cursor to the {blind.upper()} Blind {operation.title()} "
                "button in Balatro, then press Enter here."
            )
            window = locator.find()
            point = normalize_cursor(window, cursor.position())
            points[control] = point
            print(
                f"Captured {control} -> x={point.x:.6f} y={point.y:.6f}"
            )

        layout = BlindMouseLayout(
            **{
                control.replace("-", "_"): point
                for control, point in points.items()
            }
        )
        layout.save(output)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
