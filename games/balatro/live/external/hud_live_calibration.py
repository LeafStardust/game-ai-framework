from __future__ import annotations

import argparse
import time
from pathlib import Path

from .hud_calibration import DEFAULT_OUTPUT, parse_field_value
from .hud_capture import DEFAULT_HUD_FIELD_REGIONS
from .hud_digit_templates import (
    DIGITS,
    HudDigitTemplate,
    empty_hud_digit_templates,
    load_hud_digit_templates,
    merge_hud_digit_templates,
    save_hud_digit_templates,
)
from .hud_digits import extract_hud_digit_signatures
from .hud_recognition import rgb_image_from_bgra
from .observer import ExternalBalatroObservation, ExternalBalatroObserver
from .viewport import BalatroViewport


def calibrate_live_hud_digits(
    observation: ExternalBalatroObservation,
    samples: list[tuple[str, str]],
    *,
    output_path: str | Path = DEFAULT_OUTPUT,
    replace: bool = False,
):
    if observation.phase.phase != "SELECTING_HAND":
        raise ValueError(
            "live HUD calibration requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )
    if not samples:
        raise ValueError("at least one HUD calibration sample is required")

    output = Path(output_path)
    if replace or not output.exists():
        templates = empty_hud_digit_templates()
    else:
        templates = load_hud_digit_templates(output)

    viewport = BalatroViewport(observation.frame)
    additions = []
    for field, number in samples:
        region_rect = DEFAULT_HUD_FIELD_REGIONS.get(field)
        if region_rect is None:
            raise ValueError(f"unknown HUD field: {field}")
        region = viewport.crop(region_rect)
        image = rgb_image_from_bgra(region.width, region.height, region.bgra)
        signatures = extract_hud_digit_signatures(
            image,
            field,
            expected_digits=len(number),
            columns=templates.columns,
            rows=templates.rows,
        )
        additions.extend(
            HudDigitTemplate(digit, signature)
            for digit, signature in zip(number, signatures)
        )

    templates = merge_hud_digit_templates(templates, additions)
    save_hud_digit_templates(templates, output)
    return templates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append HUD digit templates directly from a live Steam Balatro hand."
    )
    parser.add_argument("values", nargs="+", metavar="FIELD=INTEGER")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--phase-templates",
        default="balatro-phase-templates.json",
    )
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    try:
        samples = [parse_field_value(value) for value in args.values]
    except ValueError as error:
        parser.error(str(error))

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring the labeled dealt hand to the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    try:
        with ExternalBalatroObserver.from_template_file(args.phase_templates) as observer:
            observation = observer.observe()
        templates = calibrate_live_hud_digits(
            observation,
            samples,
            output_path=args.output,
            replace=args.replace,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    coverage = sorted(templates.coverage, key=int)
    missing = [digit for digit in DIGITS if digit not in templates.coverage]
    print("Digit coverage: " + (", ".join(coverage) if coverage else "none"))
    print("Missing digits: " + (", ".join(missing) if missing else "none"))
    print(f"Recognition calibration complete: {templates.complete}")
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
