from __future__ import annotations

import argparse
import json
from pathlib import Path

from .card_aligned_features import aligned_templates_from_labeled_images
from .card_templates import (
    TEMPLATE_COLUMNS,
    TEMPLATE_ROWS,
    coverage_report,
    load_card_template_set,
    merge_card_template_sets,
    save_card_template_set,
)


def load_labeled_identity_manifest(path: str | Path) -> tuple[list[Path], list[str]]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cards = payload.get("cards", [])
    if not cards:
        raise ValueError("card identity manifest contains no cards")

    image_paths = []
    labels = []
    for expected_index, card in enumerate(cards):
        index = int(card.get("index", expected_index))
        if index != expected_index:
            raise ValueError("card identity manifest indexes must be sequential")

        file_value = card.get("file")
        label = card.get("label")
        if not file_value or not label:
            raise ValueError("each card identity manifest entry needs file and label")

        image_path = Path(file_value)
        if not image_path.is_absolute():
            image_path = manifest_path.parent / image_path
        image_paths.append(image_path)
        labels.append(str(label))

    return image_paths, labels


def calibrate_card_templates(
    manifest_path: str | Path,
    output_path: str | Path,
    *,
    append: bool = True,
) -> dict:
    image_paths, labels = load_labeled_identity_manifest(manifest_path)
    additions = aligned_templates_from_labeled_images(
        image_paths,
        labels,
        columns=TEMPLATE_COLUMNS,
        rows=TEMPLATE_ROWS,
    )

    output = Path(output_path)
    base = None
    if append and output.exists():
        base = load_card_template_set(output)
    merged = merge_card_template_sets(base, additions)
    save_card_template_set(output, merged)
    return coverage_report(merged)


def calibrate_card_template_manifests(
    manifest_paths: list[str | Path],
    output_path: str | Path,
    *,
    replace: bool = False,
) -> dict:
    if not manifest_paths:
        raise ValueError("at least one card identity manifest is required")

    report = None
    for index, manifest_path in enumerate(manifest_paths):
        report = calibrate_card_templates(
            manifest_path,
            output_path,
            append=not replace or index > 0,
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Balatro rank/suit visual templates from labeled card crops."
    )
    parser.add_argument(
        "--manifest",
        action="append",
        dest="manifests",
        help=(
            "Labeled identity manifest. Repeat this option to rebuild from "
            "multiple calibration datasets."
        ),
    )
    parser.add_argument(
        "--output",
        default="balatro-card-templates.json",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the output template set before the first manifest.",
    )
    args = parser.parse_args()

    manifests = args.manifests or ["balatro-card-identities/labels.json"]

    try:
        report = calibrate_card_template_manifests(
            manifests,
            args.output,
            replace=args.replace,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    print("Rank coverage: " + ", ".join(report["ranks"]))
    print("Suit coverage: " + ", ".join(report["suits"]))
    print(
        "Missing ranks: "
        + (", ".join(report["missing_ranks"]) or "none")
    )
    print(
        "Missing suits: "
        + (", ".join(report["missing_suits"]) or "none")
    )
    print(f"Recognition calibration complete: {report['complete']}")
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
