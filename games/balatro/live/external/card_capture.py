from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .capture import save_bgra_png, save_frame_png
from .observer import ExternalBalatroObservation, ExternalBalatroObserver
from .viewport import BalatroViewport, NormalizedRect


DEFAULT_HAND_REGION = NormalizedRect(0.15, 0.50, 0.84, 0.49)


def save_card_diagnostic(
    observation: ExternalBalatroObservation,
    output_prefix: str | Path,
    *,
    hand_region: NormalizedRect = DEFAULT_HAND_REGION,
) -> dict:
    if observation.phase.phase != "SELECTING_HAND":
        raise ValueError(
            "card diagnostic requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    prefix = Path(output_prefix)
    full_path = Path(f"{prefix}-full.png")
    hand_path = Path(f"{prefix}-hand.png")
    metadata_path = Path(f"{prefix}.json")

    frame = observation.frame
    viewport = BalatroViewport(frame)
    hand = viewport.crop(hand_region)

    save_frame_png(frame, full_path)
    save_bgra_png(hand.width, hand.height, hand.bgra, hand_path)

    metadata = {
        "phase": observation.phase.phase,
        "phase_confidence": observation.phase.confidence,
        "frame": {
            "width": frame.width,
            "height": frame.height,
            "window": {
                "left": frame.window.client_rect.left,
                "top": frame.window.client_rect.top,
                "width": frame.window.client_rect.width,
                "height": frame.window.client_rect.height,
            },
        },
        "hand_region": {
            "normalized": {
                "left": hand_region.left,
                "top": hand_region.top,
                "width": hand_region.width,
                "height": hand_region.height,
            },
            "pixels": {
                "left": hand.pixel_rect.left,
                "top": hand.pixel_rect.top,
                "width": hand.pixel_rect.width,
                "height": hand.pixel_rect.height,
            },
        },
        "files": {
            "full": str(full_path),
            "hand": str(hand_path),
        },
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a real Steam Balatro hand for card-recognition development."
    )
    parser.add_argument(
        "--templates",
        default="balatro-phase-templates.json",
    )
    parser.add_argument(
        "--output-prefix",
        default="balatro-card-diagnostic",
    )
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    parser.add_argument("--left", type=float, default=DEFAULT_HAND_REGION.left)
    parser.add_argument("--top", type=float, default=DEFAULT_HAND_REGION.top)
    parser.add_argument("--width", type=float, default=DEFAULT_HAND_REGION.width)
    parser.add_argument("--height", type=float, default=DEFAULT_HAND_REGION.height)
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    try:
        hand_region = NormalizedRect(
            args.left,
            args.top,
            args.width,
            args.height,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring Balatro to a dealt hand in the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    with ExternalBalatroObserver.from_template_file(args.templates) as observer:
        observation = observer.observe()

    try:
        metadata = save_card_diagnostic(
            observation,
            args.output_prefix,
            hand_region=hand_region,
        )
    except ValueError as error:
        parser.error(str(error))

    files = metadata["files"]
    print(f"Detected phase: {metadata['phase']}")
    print(f"Saved full frame -> {files['full']}")
    print(f"Saved hand crop -> {files['hand']}")
    print(f"Saved metadata -> {args.output_prefix}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
