from __future__ import annotations

import argparse
import time

from .card_capture import DEFAULT_HAND_REGION
from .card_identity import extract_card_identity_regions
from .card_locator import locate_card_faces
from .card_recognition import CardRecognition, recognize_identity_region
from .card_template_format import load_card_template_set
from .card_templates import coverage_report, parse_card_label
from .observer import ExternalBalatroObserver
from .viewport import BalatroViewport


def validate_recognitions(
    expected_labels: list[str],
    recognitions: list[CardRecognition],
) -> list[bool]:
    if len(expected_labels) != len(recognitions):
        raise ValueError(
            f"expected {len(expected_labels)} cards, recognized {len(recognitions)}"
        )

    results = []
    for expected, recognition in zip(expected_labels, recognitions):
        rank, suit = parse_card_label(expected)
        results.append(
            recognition.rank.label == rank and recognition.suit.label == suit
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Balatro card recognition on an unseen live Steam hand."
    )
    parser.add_argument("--expected", nargs="+", required=True)
    parser.add_argument("--phase-templates", default="balatro-phase-templates.json")
    parser.add_argument("--card-templates", default="balatro-card-templates.json")
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    templates = load_card_template_set(args.card_templates)
    report = coverage_report(templates)
    if not report["complete"]:
        parser.error(
            "card calibration is incomplete; missing ranks="
            + ",".join(report["missing_ranks"])
            + " missing suits="
            + ",".join(report["missing_suits"])
        )

    try:
        for label in args.expected:
            parse_card_label(label)
    except ValueError as error:
        parser.error(str(error))

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring the unseen dealt hand to the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    with ExternalBalatroObserver.from_template_file(args.phase_templates) as observer:
        observation = observer.observe()

    if observation.phase.phase != "SELECTING_HAND":
        parser.error(
            "card validation requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    viewport = BalatroViewport(observation.frame)
    hand = viewport.crop(DEFAULT_HAND_REGION)
    cards = locate_card_faces(hand)
    identities = extract_card_identity_regions(viewport, cards)
    recognitions = [
        recognize_identity_region(identity.region, templates)
        for identity in identities
    ]

    try:
        results = validate_recognitions(args.expected, recognitions)
    except ValueError as error:
        parser.error(str(error))

    passes = 0
    for index, (expected, recognition, passed) in enumerate(
        zip(args.expected, recognitions, results)
    ):
        expected_rank, expected_suit = parse_card_label(expected)
        status = "PASS" if passed else "FAIL"
        passes += int(passed)
        print(
            f"{index}: {status} expected={expected_rank} {expected_suit} "
            f"detected={recognition.label} "
            f"rank_distance={recognition.rank.distance:.4f} "
            f"rank_margin={recognition.rank.margin:.4f} "
            f"suit_distance={recognition.suit.distance:.4f} "
            f"suit_margin={recognition.suit.margin:.4f}"
        )

    print(f"Unseen card recognition validation: {passes}/{len(results)} matches.")
    return 0 if passes == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
