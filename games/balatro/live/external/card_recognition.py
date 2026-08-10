from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .card_aligned_features import (
    aligned_rank_shape_signature,
    aligned_suit_color_signature,
)
from .card_capture import DEFAULT_HAND_REGION
from .card_identity import extract_card_identity_regions
from .card_locator import locate_card_faces
from .card_template_format import load_card_template_set
from .card_templates import CardTemplateSet, CardVisualTemplate, RGBImage
from .observer import ExternalBalatroObserver
from .viewport import BalatroViewport, FrameRegion


@dataclass(frozen=True)
class CardLabelMatch:
    label: str
    distance: float
    margin: float
    confidence: float
    runner_up: str | None


@dataclass(frozen=True)
class CardRecognition:
    rank: CardLabelMatch
    suit: CardLabelMatch

    @property
    def label(self) -> str:
        return f"{self.rank.label} {self.suit.label}"


def recognize_card_image(
    image: RGBImage,
    templates: CardTemplateSet,
) -> CardRecognition:
    suit_signature = aligned_suit_color_signature(image)
    rank_signature = aligned_rank_shape_signature(
        image,
        suit_signature,
        columns=templates.columns,
        rows=templates.rows,
    )
    return CardRecognition(
        rank=_match_signature(rank_signature, templates.ranks),
        suit=_match_signature(suit_signature, templates.suits),
    )


def recognize_identity_region(
    region: FrameRegion,
    templates: CardTemplateSet,
) -> CardRecognition:
    return recognize_card_image(_rgb_image_from_region(region), templates)


def _match_signature(
    signature: tuple[int, ...],
    templates: tuple[CardVisualTemplate, ...],
) -> CardLabelMatch:
    if not templates:
        raise ValueError("card recognition requires at least one template")

    distances: dict[str, float] = {}
    for template in templates:
        if len(template.signature) != len(signature):
            raise ValueError("card template signature dimensions do not match")
        distance = sum(
            abs(left - right)
            for left, right in zip(signature, template.signature)
        ) / (len(signature) * 255.0)
        current = distances.get(template.label)
        if current is None or distance < current:
            distances[template.label] = distance

    ranked = sorted(distances.items(), key=lambda item: item[1])
    label, distance = ranked[0]
    if len(ranked) > 1:
        runner_up, runner_distance = ranked[1]
        margin = runner_distance - distance
    else:
        runner_up = None
        margin = 1.0 - distance

    return CardLabelMatch(
        label=label,
        distance=distance,
        margin=max(0.0, margin),
        confidence=max(0.0, min(1.0, 1.0 - distance)),
        runner_up=runner_up,
    )


def _rgb_image_from_region(region: FrameRegion) -> RGBImage:
    rgb = bytearray(region.width * region.height * 3)
    destination = 0
    for index in range(0, len(region.bgra), 4):
        blue, green, red = region.bgra[index : index + 3]
        rgb[destination : destination + 3] = bytes((red, green, blue))
        destination += 3
    return RGBImage(region.width, region.height, bytes(rgb))


def _serialize(recognitions: list[CardRecognition]) -> dict:
    return {
        "count": len(recognitions),
        "cards": [
            {
                "index": index,
                "rank": _serialize_match(card.rank),
                "suit": _serialize_match(card.suit),
            }
            for index, card in enumerate(recognitions)
        ],
    }


def _serialize_match(match: CardLabelMatch) -> dict:
    return {
        "label": match.label,
        "distance": match.distance,
        "margin": match.margin,
        "confidence": match.confidence,
        "runner_up": match.runner_up,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recognize ranks and suits in a live Steam Balatro hand."
    )
    parser.add_argument("--phase-templates", default="balatro-phase-templates.json")
    parser.add_argument("--card-templates", default="balatro-card-templates.json")
    parser.add_argument("--output", default="balatro-card-recognition.json")
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    try:
        templates = load_card_template_set(args.card_templates)
    except ValueError as error:
        parser.error(str(error))

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring Balatro to a dealt hand in the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    with ExternalBalatroObserver.from_template_file(args.phase_templates) as observer:
        observation = observer.observe()

    if observation.phase.phase != "SELECTING_HAND":
        parser.error(
            "card recognition requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    viewport = BalatroViewport(observation.frame)
    hand = viewport.crop(DEFAULT_HAND_REGION)
    cards = locate_card_faces(hand)
    if not cards:
        parser.error("no playing cards located")

    identities = extract_card_identity_regions(viewport, cards)
    recognitions = [
        recognize_identity_region(identity.region, templates)
        for identity in identities
    ]
    Path(args.output).write_text(
        json.dumps(_serialize(recognitions), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Recognized cards: {len(recognitions)}")
    for index, card in enumerate(recognitions):
        print(
            f"{index}: {card.label} "
            f"rank_distance={card.rank.distance:.4f} "
            f"rank_margin={card.rank.margin:.4f} "
            f"suit_distance={card.suit.distance:.4f} "
            f"suit_margin={card.suit.margin:.4f}"
        )
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
