from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .card_calibration import load_labeled_identity_manifest
from .card_recognition import recognize_card_image
from .card_template_format import load_card_template_set
from .card_templates import load_rgb_png, parse_card_label


DEFAULT_MANIFESTS = (
    "balatro-card-identities/labels.json",
    "balatro-card-identities-02/labels.json",
    "balatro-card-identities-03/labels.json",
    "balatro-card-unseen-01/labels.json",
)


def exact_rank_collisions(templates_path: str | Path) -> list[tuple[tuple[str, ...], int]]:
    templates = load_card_template_set(templates_path)
    groups: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for template in templates.ranks:
        groups[template.signature].add(template.label)

    collisions = []
    for signature, labels in groups.items():
        if len(labels) > 1:
            collisions.append((tuple(sorted(labels)), hash(signature)))
    return sorted(collisions)


def rank_failures(
    manifest_paths: list[str | Path],
    templates_path: str | Path,
) -> list[dict]:
    templates = load_card_template_set(templates_path)
    failures = []

    for manifest_path in manifest_paths:
        manifest = Path(manifest_path)
        image_paths, labels = load_labeled_identity_manifest(manifest)
        for index, (image_path, label) in enumerate(zip(image_paths, labels)):
            expected_rank, _ = parse_card_label(label)
            match = recognize_card_image(load_rgb_png(image_path), templates).rank
            if match.label != expected_rank or match.margin == 0.0:
                failures.append(
                    {
                        "manifest": str(manifest),
                        "index": index,
                        "expected": expected_rank,
                        "detected": match.label,
                        "runner_up": match.runner_up,
                        "distance": match.distance,
                        "margin": match.margin,
                    }
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose collisions and rank failures in Balatro card templates."
    )
    parser.add_argument(
        "--manifest",
        action="append",
        dest="manifests",
        help="Labeled card manifest to replay. Repeat for multiple datasets.",
    )
    parser.add_argument("--templates", default="balatro-card-templates.json")
    args = parser.parse_args()

    manifests = args.manifests or list(DEFAULT_MANIFESTS)
    collisions = exact_rank_collisions(args.templates)
    failures = rank_failures(manifests, args.templates)

    print(f"Exact cross-rank signature collisions: {len(collisions)}")
    for labels, _ in collisions:
        print("COLLISION: " + " / ".join(labels))

    print(f"Ambiguous or failing rank samples: {len(failures)}")
    for item in failures:
        print(
            f"{item['manifest']}[{item['index']}]: "
            f"expected={item['expected']} detected={item['detected']} "
            f"runner_up={item['runner_up']} distance={item['distance']:.4f} "
            f"margin={item['margin']:.4f}"
        )

    return 0 if not collisions and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
