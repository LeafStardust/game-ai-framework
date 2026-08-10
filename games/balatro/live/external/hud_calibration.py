from __future__ import annotations

import argparse
from pathlib import Path

from .card_templates import load_rgb_png
from .hud_digit_templates import (
    DIGITS,
    HudDigitTemplate,
    empty_hud_digit_templates,
    load_hud_digit_templates,
    merge_hud_digit_templates,
    save_hud_digit_templates,
)
from .hud_digits import extract_hud_digit_signatures


DEFAULT_OUTPUT = "balatro-hud-digit-templates.json"
DEFAULT_INPUT_PREFIX = "balatro-hud-diagnostic"


def parse_field_value(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError("HUD calibration values must use FIELD=INTEGER")
    field, raw_number = value.split("=", 1)
    field = field.strip()
    raw_number = raw_number.strip()
    if not field:
        raise ValueError("HUD calibration field cannot be empty")
    if not raw_number or not raw_number.isdigit():
        raise ValueError(f"HUD calibration value must be a non-negative integer: {value}")
    return field, raw_number


def calibrate_hud_digits(
    samples: list[tuple[str, str]],
    *,
    input_prefix: str | Path = DEFAULT_INPUT_PREFIX,
    output_path: str | Path = DEFAULT_OUTPUT,
    replace: bool = False,
):
    if not samples:
        raise ValueError("at least one HUD calibration sample is required")

    output = Path(output_path)
    if replace or not output.exists():
        templates = empty_hud_digit_templates()
    else:
        templates = load_hud_digit_templates(output)

    prefix = Path(input_prefix)
    additions = []
    for field, number in samples:
        image_path = Path(f"{prefix}-{field}.png")
        image = load_rgb_png(image_path)
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
        description="Build HUD digit templates from labeled Balatro diagnostic crops."
    )
    parser.add_argument(
        "values",
        nargs="+",
        metavar="FIELD=INTEGER",
    )
    parser.add_argument("--input-prefix", default=DEFAULT_INPUT_PREFIX)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    try:
        samples = [parse_field_value(value) for value in args.values]
        templates = calibrate_hud_digits(
            samples,
            input_prefix=args.input_prefix,
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
