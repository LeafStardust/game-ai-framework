from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .capture import save_bgra_png
from .card_capture import DEFAULT_HAND_REGION
from .card_locator import CardFaceLocation, locate_card_faces
from .card_templates import parse_card_label
from .observer import ExternalBalatroObserver
from .viewport import BalatroViewport, FrameRegion, NormalizedRect


IDENTITY_WIDTH_RATIO = 0.48
IDENTITY_HEIGHT_RATIO = 0.46


@dataclass(frozen=True)
class CardIdentityRegion:
    card: CardFaceLocation
    rect: NormalizedRect
    region: FrameRegion


def card_identity_rect(
    card: CardFaceLocation,
    *,
    width_ratio: float = IDENTITY_WIDTH_RATIO,
    height_ratio: float = IDENTITY_HEIGHT_RATIO,
) -> NormalizedRect:
    if not 0.0 < width_ratio <= 1.0:
        raise ValueError("width_ratio must be between 0 and 1")
    if not 0.0 < height_ratio <= 1.0:
        raise ValueError("height_ratio must be between 0 and 1")

    source = card.normalized_rect
    return NormalizedRect(
        source.left,
        source.top,
        source.width * width_ratio,
        source.height * height_ratio,
    )


def extract_card_identity_regions(
    viewport: BalatroViewport,
    cards: list[CardFaceLocation],
    *,
    width_ratio: float = IDENTITY_WIDTH_RATIO,
    height_ratio: float = IDENTITY_HEIGHT_RATIO,
) -> list[CardIdentityRegion]:
    identities = []
    for card in cards:
        rect = card_identity_rect(
            card,
            width_ratio=width_ratio,
            height_ratio=height_ratio,
        )
        identities.append(CardIdentityRegion(card, rect, viewport.crop(rect)))
    return identities


def save_card_identity_diagnostic(
    identities: list[CardIdentityRegion],
    output_dir: str | Path,
) -> dict:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    cards = []
    for index, identity in enumerate(identities):
        path = directory / f"card-{index:02d}.png"
        region = identity.region
        save_bgra_png(region.width, region.height, region.bgra, path)
        cards.append(
            {
                "index": index,
                "file": str(path),
                "center": {
                    "x": identity.card.center.x,
                    "y": identity.card.center.y,
                },
                "identity_rect": {
                    "left": identity.rect.left,
                    "top": identity.rect.top,
                    "width": identity.rect.width,
                    "height": identity.rect.height,
                },
                "pixels": {
                    "width": region.width,
                    "height": region.height,
                },
            }
        )

    metadata = {"count": len(cards), "cards": cards}
    metadata_path = directory / "cards.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def save_card_identity_labels(
    metadata: dict,
    labels: list[str],
    output_dir: str | Path,
) -> Path:
    cards = metadata.get("cards", [])
    if len(labels) != len(cards):
        raise ValueError(
            f"label count must match card count: expected {len(cards)}, got {len(labels)}"
        )

    entries = []
    for index, (card, label) in enumerate(zip(cards, labels)):
        parse_card_label(label)
        entries.append(
            {
                "index": index,
                "file": Path(card["file"]).name,
                "label": label,
            }
        )

    path = Path(output_dir) / "labels.json"
    path.write_text(
        json.dumps({"cards": entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract rank/suit identity corners from a live Steam Balatro hand."
    )
    parser.add_argument("--templates", default="balatro-phase-templates.json")
    parser.add_argument("--output-dir", default="balatro-card-identities")
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    parser.add_argument("--width-ratio", type=float, default=IDENTITY_WIDTH_RATIO)
    parser.add_argument("--height-ratio", type=float, default=IDENTITY_HEIGHT_RATIO)
    parser.add_argument(
        "--labels",
        nargs="+",
        help="Left-to-right card labels, e.g. AH KD 10S 9C.",
    )
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring Balatro to a dealt hand in the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    with ExternalBalatroObserver.from_template_file(args.templates) as observer:
        observation = observer.observe()

    if observation.phase.phase != "SELECTING_HAND":
        parser.error(
            "card identity extraction requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    viewport = BalatroViewport(observation.frame)
    hand = viewport.crop(DEFAULT_HAND_REGION)
    cards = locate_card_faces(hand)
    if not cards:
        parser.error("no playing cards located")

    try:
        identities = extract_card_identity_regions(
            viewport,
            cards,
            width_ratio=args.width_ratio,
            height_ratio=args.height_ratio,
        )
        metadata = save_card_identity_diagnostic(identities, args.output_dir)
        label_path = None
        if args.labels is not None:
            label_path = save_card_identity_labels(
                metadata,
                args.labels,
                args.output_dir,
            )
    except ValueError as error:
        parser.error(str(error))

    print(f"Extracted card identity regions: {metadata['count']}")
    for card in metadata["cards"]:
        pixels = card["pixels"]
        print(
            f"{card['index']}: {card['file']} "
            f"size={pixels['width']}x{pixels['height']}"
        )
    print(f"Saved metadata -> {Path(args.output_dir) / 'cards.json'}")
    if label_path is not None:
        print(f"Saved labels -> {label_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
