from __future__ import annotations

import argparse
from pathlib import Path

from .blind_mouse import BLIND_TARGETS, BlindMouseLayout
from .shop_mouse_calibration import WindowsCursorProvider, normalize_cursor
from .window import BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-blind-mouse.json"


def print_status(layout: BlindMouseLayout) -> None:
    for target in ("small", "big", "boss"):
        point = getattr(layout, target)
        if point is None:
            print(f"{target} -> no")
        else:
            print(f"{target} -> x={point.x:.6f} y={point.y:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record resolution-independent Balatro blind Select-button coordinates."
        )
    )
    parser.add_argument("targets", nargs="*", choices=sorted(BLIND_TARGETS))
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    if args.status and args.targets:
        parser.error("--status cannot be combined with calibration targets")
    if args.status and args.replace:
        parser.error("--status cannot be combined with --replace")
    if not args.status and not args.targets:
        parser.error("at least one blind target is required")

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
            "small": layout.small,
            "big": layout.big,
            "boss": layout.boss,
        }

        for target in args.targets:
            input(
                f"Move the cursor to the {target.upper()} Blind Select button in "
                "Balatro, then press Enter here."
            )
            window = locator.find()
            point = normalize_cursor(window, cursor.position())
            points[target] = point
            print(
                f"Captured {target} -> x={point.x:.6f} y={point.y:.6f}"
            )

        layout = BlindMouseLayout(**points)
        layout.save(output)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
