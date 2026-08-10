from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .capture import save_bgra_png, save_frame_png
from .observer import ExternalBalatroObservation, ExternalBalatroObserver
from .viewport import BalatroViewport, NormalizedRect


DEFAULT_HUD_REGION = NormalizedRect(0.00, 0.00, 0.27, 1.00)

DEFAULT_HUD_FIELD_REGIONS = {
    "ante": NormalizedRect(0.13, 0.89, 0.04, 0.06),
    "blind_target": NormalizedRect(0.17, 0.21, 0.08, 0.06),
    "discards": NormalizedRect(0.20, 0.66, 0.05, 0.08),
    "hands": NormalizedRect(0.13, 0.66, 0.05, 0.08),
    "money": NormalizedRect(0.14, 0.77, 0.11, 0.07),
    "round": NormalizedRect(0.20, 0.89, 0.05, 0.06),
    "score": NormalizedRect(0.17, 0.37, 0.08, 0.06),
}


def _rect_metadata(rect: NormalizedRect, pixel_rect) -> dict:
    return {
        "normalized": {
            "left": rect.left,
            "top": rect.top,
            "width": rect.width,
            "height": rect.height,
        },
        "pixels": {
            "left": pixel_rect.left,
            "top": pixel_rect.top,
            "width": pixel_rect.width,
            "height": pixel_rect.height,
        },
    }


def save_hud_diagnostic(
    observation: ExternalBalatroObservation,
    output_prefix: str | Path,
    *,
    hud_region: NormalizedRect = DEFAULT_HUD_REGION,
    field_regions: dict[str, NormalizedRect] | None = None,
) -> dict:
    if observation.phase.phase != "SELECTING_HAND":
        raise ValueError(
            "HUD diagnostic requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    regions = field_regions or DEFAULT_HUD_FIELD_REGIONS
    prefix = Path(output_prefix)
    full_path = Path(f"{prefix}-full.png")
    panel_path = Path(f"{prefix}-panel.png")
    metadata_path = Path(f"{prefix}.json")

    frame = observation.frame
    viewport = BalatroViewport(frame)
    hud = viewport.crop(hud_region)

    save_frame_png(frame, full_path)
    save_bgra_png(hud.width, hud.height, hud.bgra, panel_path)

    fields = {}
    for name in sorted(regions):
        region = viewport.crop(regions[name])
        path = Path(f"{prefix}-{name}.png")
        save_bgra_png(region.width, region.height, region.bgra, path)
        fields[name] = {
            **_rect_metadata(regions[name], region.pixel_rect),
            "file": str(path),
        }

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
        "hud_region": {
            **_rect_metadata(hud_region, hud.pixel_rect),
            "file": str(panel_path),
        },
        "fields": fields,
        "files": {
            "full": str(full_path),
            "metadata": str(metadata_path),
            "panel": str(panel_path),
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
        description="Capture candidate HUD regions from a real Steam Balatro hand."
    )
    parser.add_argument(
        "--templates",
        default="balatro-phase-templates.json",
    )
    parser.add_argument(
        "--output-prefix",
        default="balatro-hud-diagnostic",
    )
    parser.add_argument("--prepare-delay", type=float, default=3.0)
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

    try:
        metadata = save_hud_diagnostic(observation, args.output_prefix)
    except ValueError as error:
        parser.error(str(error))

    print(f"Detected phase: {metadata['phase']}")
    print(f"Saved full frame -> {metadata['files']['full']}")
    print(f"Saved HUD panel -> {metadata['files']['panel']}")
    for name in sorted(metadata["fields"]):
        print(f"Saved {name} candidate -> {metadata['fields'][name]['file']}")
    print(f"Saved metadata -> {metadata['files']['metadata']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
