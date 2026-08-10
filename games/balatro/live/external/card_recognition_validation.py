from __future__ import annotations

import argparse
import json
from pathlib import Path

from .card_recognition import recognize_card_image
from .card_templates import (
    load_card_template_set,
    load_rgb_png,
    parse_card_label,
)


def validate_labeled_samples(
    labels_path: str | Path,
    templates_path: str | Path,
) -> list[dict]:
    labels_file = Path(labels_path)
    payload = json.loads(labels_file.read_text(encoding="utf-8"))
    templates = load_card_template_set(templates_path)
    results = []

    for item in payload.get("cards", []):
        expected_rank, expected_suit = parse_card_label(str(item["label"]))
        image_path = labels_file.parent / str(item["file"])
        recognition = recognize_card_image(load_rgb_png(image_path), templates)
        passed = (
            recognition.rank.label == expected_rank
            and recognition.suit.label == expected_suit
        )
        results.append(
            {
                "index": int(item["index"]),
                "expected_rank": expected_rank,
                "expected_suit": expected_suit,
                "detected_rank": recognition.rank.label,
                "detected_suit": recognition.suit.label,
                "rank_distance": recognition.rank.distance,
                "rank_margin": recognition.rank.margin,
                "rank_runner_up": recognition.rank.runner_up,
                "suit_distance": recognition.suit.distance,
                "suit_margin": recognition.suit.margin,
                "suit_runner_up": recognition.suit.runner_up,
                "passed": passed,
            }
        )

    if not results:
        raise ValueError("card recognition validation requires labeled samples")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay labeled Balatro card crops through the visual recognizer."
    )
    parser.add_argument(
        "--labels",
        default="balatro-card-identities/labels.json",
    )
    parser.add_argument(
        "--templates",
        default="balatro-card-templates.json",
    )
    args = parser.parse_args()

    try:
        results = validate_labeled_samples(args.labels, args.templates)
    except ValueError as error:
        parser.error(str(error))

    passed = sum(result["passed"] for result in results)
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        expected = f"{result['expected_rank']} {result['expected_suit']}"
        detected = f"{result['detected_rank']} {result['detected_suit']}"
        print(
            f"{result['index']}: {status} expected={expected} detected={detected} "
            f"rank_distance={result['rank_distance']:.4f} "
            f"rank_margin={result['rank_margin']:.4f} "
            f"rank_runner_up={result['rank_runner_up']} "
            f"suit_distance={result['suit_distance']:.4f} "
            f"suit_margin={result['suit_margin']:.4f} "
            f"suit_runner_up={result['suit_runner_up']}"
        )

    print(f"Card recognition sample validation: {passed}/{len(results)} matches.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
