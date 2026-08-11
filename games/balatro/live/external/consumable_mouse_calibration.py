from __future__ import annotations

import argparse
from pathlib import Path

from .consumable_mouse import ConsumableMouseLayout
from .shop_mouse_calibration import WindowsCursorProvider, normalize_cursor
from .window import BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-consumable-mouse.json"
CONTROLS = {"slot-0", "slot-1", "use-0", "use-1"}


def print_status(layout: ConsumableMouseLayout) -> None:
    values = {
        "slot-0": layout.slot_0,
        "slot-1": layout.slot_1,
        "use-0": layout.use_0,
        "use-1": layout.use_1,
    }
    for name, point in values.items():
        if point is None:
            print(f"{name} -> no")
        else:
            print(f"{name} -> x={point.x:.6f} y={point.y:.6f}")


def _prompt(control: str) -> str:
    if control == "slot-0":
        return (
            "Move the cursor to the left/first held consumable card in Balatro, "
            "then press Enter here."
        )
    if control == "slot-1":
        return (
            "Move the cursor to the right/second held consumable card in Balatro, "
            "then press Enter here."
        )
    slot = control.removeprefix("use-")
    return (
        f"Open held consumable slot {slot} so its Use button is visible in Balatro, "
        "move the cursor to that Use button, then press Enter here."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record resolution-independent Balatro held-consumable slots and "
            "slot-specific Use buttons."
        )
    )
    parser.add_argument("controls", nargs="*", choices=sorted(CONTROLS))
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
        parser.error("at least one consumable control is required")

    try:
        if output.exists() and not args.replace:
            layout = ConsumableMouseLayout.load(output)
        else:
            layout = ConsumableMouseLayout()

        if args.status:
            print_status(layout)
            return 0

        locator = BalatroWindowLocator()
        cursor = WindowsCursorProvider()
        points = {
            "slot-0": layout.slot_0,
            "slot-1": layout.slot_1,
            "use-0": layout.use_0,
            "use-1": layout.use_1,
        }

        for control in args.controls:
            input(_prompt(control))
            window = locator.find()
            point = normalize_cursor(window, cursor.position())
            points[control] = point
            print(
                f"Captured {control} -> x={point.x:.6f} y={point.y:.6f}"
            )

        layout = ConsumableMouseLayout(
            slot_0=points["slot-0"],
            slot_1=points["slot-1"],
            use_0=points["use-0"],
            use_1=points["use-1"],
        )
        layout.save(output)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
