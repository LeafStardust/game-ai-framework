from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from .observer import ExternalBalatroObserver
from .phase_store import load_phase_templates


REQUIRED_PHASES = {
    "BLIND_SELECT",
    "ROUND_EVAL",
    "SELECTING_HAND",
    "SHOP",
}


def validate_template_set(path: str | Path) -> Counter:
    templates = load_phase_templates(path)
    if not templates:
        raise ValueError("phase template file contains no templates")

    counts = Counter(template.phase for template in templates)
    missing = sorted(REQUIRED_PHASES - set(counts))
    if missing:
        raise ValueError(
            "phase template file is missing required phase(s): "
            + ", ".join(missing)
        )

    dimensions = {
        (template.signature.columns, template.signature.rows)
        for template in templates
    }
    if len(dimensions) != 1:
        raise ValueError("phase templates use inconsistent grid dimensions")

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate external Balatro visual phase recognition."
    )
    parser.add_argument(
        "--templates",
        default="balatro-phase-templates.json",
    )
    parser.add_argument(
        "--expected",
        choices=sorted(REQUIRED_PHASES),
    )
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.10)
    args = parser.parse_args()

    if args.samples < 1:
        parser.error("--samples must be at least 1")

    try:
        counts = validate_template_set(args.templates)
    except ValueError as error:
        parser.error(str(error))

    print(
        "Templates: "
        + ", ".join(
            f"{phase}={counts[phase]}"
            for phase in sorted(REQUIRED_PHASES)
        )
    )

    if args.expected is None:
        print("Template set verified.")
        return 0

    failures = 0
    with ExternalBalatroObserver.from_template_file(args.templates) as observer:
        for index in range(args.samples):
            observation = observer.observe()
            detection = observation.phase
            ranking = observer.recognizer.rank(observation.frame)
            runner_up = ranking[1] if len(ranking) > 1 else None
            margin = (
                runner_up.distance - detection.distance
                if runner_up is not None
                else 1.0 - detection.distance
            )

            status = "PASS" if detection.phase == args.expected else "FAIL"
            if status == "FAIL":
                failures += 1

            competitor = (
                f"{runner_up.phase}:{runner_up.distance:.4f}"
                if runner_up is not None
                else "none"
            )
            print(
                f"{index + 1}/{args.samples} {status} "
                f"expected={args.expected} detected={detection.phase} "
                f"distance={detection.distance:.4f} "
                f"confidence={detection.confidence:.4f} "
                f"runner_up={competitor} margin={margin:.4f}"
            )

            if index + 1 < args.samples and args.interval > 0:
                time.sleep(args.interval)

    if failures:
        print(f"Phase validation failed: {failures}/{args.samples} mismatches.")
        return 1

    print(f"Phase validation passed: {args.samples}/{args.samples} matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
