from __future__ import annotations

import argparse
import time

from .hud_calibration import parse_field_value
from .hud_capture import DEFAULT_HUD_FIELD_REGIONS
from .hud_digit_templates import load_hud_digit_templates
from .hud_recognition import recognize_hud_number, rgb_image_from_bgra
from .observer import ExternalBalatroObserver
from .viewport import BalatroViewport


DEFAULT_TEMPLATES = "balatro-hud-digit-templates.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate HUD number recognition against a live Steam Balatro hand."
    )
    parser.add_argument("--templates", default=DEFAULT_TEMPLATES)
    parser.add_argument(
        "--phase-templates",
        default="balatro-phase-templates.json",
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="FIELD=INTEGER",
    )
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    try:
        expected = dict(parse_field_value(value) for value in args.expect)
        templates = load_hud_digit_templates(args.templates)

        if args.prepare_delay > 0:
            print(
                f"Capture starts in {args.prepare_delay:g}s; "
                "bring the dealt hand to the foreground.",
                flush=True,
            )
            time.sleep(args.prepare_delay)

        with ExternalBalatroObserver.from_template_file(args.phase_templates) as observer:
            observation = observer.observe()
        if observation.phase.phase != "SELECTING_HAND":
            parser.error(
                "HUD recognition validation requires SELECTING_HAND, got "
                f"{observation.phase.phase}"
            )

        viewport = BalatroViewport(observation.frame)
        failures = 0
        for field in sorted(DEFAULT_HUD_FIELD_REGIONS):
            region = viewport.crop(DEFAULT_HUD_FIELD_REGIONS[field])
            image = rgb_image_from_bgra(region.width, region.height, region.bgra)
            recognition = recognize_hud_number(image, field, templates)
            expected_value = expected.get(field)
            passed = expected_value is None or recognition.value == int(expected_value)
            failures += int(not passed)
            status = "PASS" if passed else "FAIL"
            print(
                f"{field}: {status} detected={recognition.value}"
                + (
                    f" expected={expected_value}"
                    if expected_value is not None
                    else ""
                )
            )
            for index, match in enumerate(recognition.digits):
                runner = match.runner_up if match.runner_up is not None else "none"
                margin = (
                    f"{match.margin:.4f}"
                    if match.margin is not None
                    else "none"
                )
                print(
                    f"  digit[{index}]={match.digit} "
                    f"distance={match.distance:.4f} "
                    f"runner_up={runner} margin={margin}"
                )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if expected:
        passed_count = len(expected) - failures
        print(f"HUD recognition validation: {passed_count}/{len(expected)} matches.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
