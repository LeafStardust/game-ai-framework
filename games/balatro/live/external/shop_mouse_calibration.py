from __future__ import annotations

import argparse
import ctypes
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .shop_mouse import (
    ShopClickSequence,
    ShopMouseLayout,
    ShopPointerStep,
)
from .viewport import NormalizedPoint, PixelPoint
from .window import BalatroWindow, BalatroWindowLocator


DEFAULT_OUTPUT = "balatro-shop-mouse.json"
AREA_NAMES = {"main", "boosters", "vouchers"}
CONTROL_NAMES = {"end_shop", "reroll"}
STEP_OPS = {"move", "click"}


class CursorProvider(Protocol):

    def position(self) -> PixelPoint: ...


class WindowsCursorProvider:

    class _Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("shop mouse calibration requires Windows")
        self.user32 = ctypes.windll.user32
        try:
            self.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

    def position(self) -> PixelPoint:
        point = self._Point()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise RuntimeError("unable to read Windows cursor position")
        return PixelPoint(int(point.x), int(point.y))


@dataclass(frozen=True)
class CalibrationTarget:
    area: str
    index: int | None
    op: str

    @property
    def key(self) -> tuple[str, int | None]:
        return self.area, self.index

    @property
    def label(self) -> str:
        if self.index is None:
            return self.area
        return f"{self.area}:{self.index}"


def parse_target(value: str) -> CalibrationTarget:
    parts = [part.strip().lower() for part in value.split(":")]

    if len(parts) == 2 and parts[0] in CONTROL_NAMES:
        area, op = parts
        index = None
    elif len(parts) == 3 and parts[0] in AREA_NAMES:
        area, raw_index, op = parts
        try:
            index = int(raw_index)
        except ValueError as error:
            raise ValueError(f"shop calibration slot must be an integer: {value}") from error
        if index < 0:
            raise ValueError(f"shop calibration slot cannot be negative: {value}")
    else:
        raise ValueError(
            "shop calibration targets must use AREA:INDEX:OP or CONTROL:OP"
        )

    if op not in STEP_OPS:
        raise ValueError(f"shop calibration op must be move or click: {value}")

    return CalibrationTarget(area=area, index=index, op=op)


def normalize_cursor(window: BalatroWindow, point: PixelPoint) -> NormalizedPoint:
    rect = window.client_rect
    if not (
        rect.left <= point.x < rect.right
        and rect.top <= point.y < rect.bottom
    ):
        raise ValueError(
            "cursor must be inside the Balatro client area when a calibration step is recorded"
        )

    width_scale = max(1, rect.width - 1)
    height_scale = max(1, rect.height - 1)
    return NormalizedPoint(
        (point.x - rect.left) / width_scale,
        (point.y - rect.top) / height_scale,
    )


def capture_steps(
    targets: list[CalibrationTarget],
    *,
    locator: BalatroWindowLocator,
    cursor: CursorProvider,
    delay: float = 0.0,
    prompt=input,
) -> dict[tuple[str, int | None], list[ShopPointerStep]]:
    captured: dict[tuple[str, int | None], list[ShopPointerStep]] = {}

    for target in targets:
        prompt(
            f"Move the cursor to {target.label} ({target.op}) in Balatro, "
            "then press Enter here."
        )
        window = locator.find()
        point = normalize_cursor(window, cursor.position())
        captured.setdefault(target.key, []).append(
            ShopPointerStep(
                op=target.op,
                point=point,
                delay=delay,
            )
        )
        print(
            f"Captured {target.label}:{target.op} -> "
            f"x={point.x:.6f} y={point.y:.6f}"
        )

    return captured


def merge_capture(
    layout: ShopMouseLayout,
    captured: dict[tuple[str, int | None], list[ShopPointerStep]],
) -> ShopMouseLayout:
    main = dict(layout.main)
    boosters = dict(layout.boosters)
    vouchers = dict(layout.vouchers)
    end_shop = layout.end_shop
    reroll = layout.reroll

    for (area, index), steps in captured.items():
        sequence = ShopClickSequence(tuple(steps))
        if area == "main":
            main[int(index)] = sequence
        elif area == "boosters":
            boosters[int(index)] = sequence
        elif area == "vouchers":
            vouchers[int(index)] = sequence
        elif area == "end_shop":
            end_shop = sequence
        elif area == "reroll":
            reroll = sequence
        else:
            raise ValueError(f"unsupported shop calibration area: {area}")

    return ShopMouseLayout(
        main=main,
        boosters=boosters,
        vouchers=vouchers,
        end_shop=end_shop,
        reroll=reroll,
    )


def print_status(layout: ShopMouseLayout) -> None:
    print("main slots -> " + _slot_status(layout.main))
    print("booster slots -> " + _slot_status(layout.boosters))
    print("voucher slots -> " + _slot_status(layout.vouchers))
    print(f"end_shop -> {'yes' if layout.end_shop is not None else 'no'}")
    print(f"reroll -> {'yes' if layout.reroll is not None else 'no'}")


def _slot_status(area: dict[int, ShopClickSequence]) -> str:
    if not area:
        return "none"
    return ", ".join(
        f"{index}({len(sequence.steps)} steps)"
        for index, sequence in sorted(area.items())
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record resolution-independent Balatro shop mouse coordinates. "
            "Targets use main:0:move, main:0:click, vouchers:0:click, "
            "end_shop:click, etc."
        )
    )
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="delay after each recorded pointer step during playback",
    )
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.status and args.targets:
        parser.error("--status cannot be combined with calibration targets")
    if args.status and args.replace:
        parser.error("--status cannot be combined with --replace")
    if not args.status and not args.targets:
        parser.error("at least one calibration target is required")

    try:
        if output.exists() and not args.replace:
            layout = ShopMouseLayout.load(output)
        else:
            layout = ShopMouseLayout()

        if args.status:
            print_status(layout)
            return 0

        targets = [parse_target(value) for value in args.targets]
        captured = capture_steps(
            targets,
            locator=BalatroWindowLocator(),
            cursor=WindowsCursorProvider(),
            delay=args.delay,
        )
        layout = merge_capture(layout, captured)
        layout.save(output)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print_status(layout)
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
