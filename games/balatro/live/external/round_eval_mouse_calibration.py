from __future__ import annotations

import argparse
from pathlib import Path

from .round_eval_mouse import RoundEvalMouseLayout
from .shop_mouse_calibration import WindowsCursorProvider, normalize_cursor
from .window import BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-round-eval-mouse.json"


def print_status(layout: RoundEvalMouseLayout) -> None:
    point = layout.cash_out
    if point is None:
        print("cash-out -> no")
    else:
        print(f"cash-out -> x={point.x:.6f} y={point.y:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record the resolution-independent Balatro Cash Out coordinate."
    )
    parser.add_argument("control", nargs="?", choices=["cash-out"])
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status and args.control:
        parser.error("--status cannot be combined with a calibration control")
    if args.status and args.replace:
        parser.error("--status cannot be combined with --replace")
    if not args.status and args.control is None:
        parser.error("cash-out control is required")

    output = Path(args.output)
    try:
        if output.exists() and not args.replace:
            layout = RoundEvalMouseLayout.load(output)
        else:
            layout = RoundEvalMouseLayout()

        if args.status:
            print_status(layout)
            return 0

        input(
            "Move the cursor to the Cash Out button in Balatro, then press Enter here."
        )
        window = BalatroWindowLocator().find()
        point = normalize_cursor(window, WindowsCursorProvider().position())
        layout = RoundEvalMouseLayout(cash_out=point)
        layout.save(output)
        print(f"Captured cash-out -> x={point.x:.6f} y={point.y:.6f}")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
