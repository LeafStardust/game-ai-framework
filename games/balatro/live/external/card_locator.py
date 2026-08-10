from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from .card_capture import DEFAULT_HAND_REGION
from .observer import ExternalBalatroObserver
from .viewport import BalatroViewport, FrameRegion, NormalizedPoint, NormalizedRect, PixelRect


@dataclass(frozen=True)
class CardFaceLocation:
    local_rect: PixelRect
    normalized_rect: NormalizedRect
    density: float

    @property
    def center(self) -> NormalizedPoint:
        return self.normalized_rect.center


def locate_card_faces(
    region: FrameRegion,
    *,
    sample_step: int = 2,
    min_brightness: int = 165,
    max_channel_spread: int = 70,
) -> list[CardFaceLocation]:
    if sample_step < 1:
        raise ValueError("sample_step must be positive")
    if not 0 <= min_brightness <= 255:
        raise ValueError("min_brightness must be between 0 and 255")
    if not 0 <= max_channel_spread <= 255:
        raise ValueError("max_channel_spread must be between 0 and 255")

    columns = (region.width + sample_step - 1) // sample_step
    rows = (region.height + sample_step - 1) // sample_step
    mask = bytearray(columns * rows)

    for row in range(rows):
        y = min(region.height - 1, row * sample_step)
        for column in range(columns):
            x = min(region.width - 1, column * sample_step)
            index = (y * region.width + x) * 4
            blue, green, red = region.bgra[index : index + 3]
            high = max(red, green, blue)
            low = min(red, green, blue)
            brightness = (red + green + blue) // 3
            if brightness >= min_brightness and high - low <= max_channel_spread:
                mask[row * columns + column] = 1

    visited = bytearray(len(mask))
    candidates: list[CardFaceLocation] = []
    min_width = max(12, round(region.width * 0.025))
    max_width = max(min_width, round(region.width * 0.18))
    min_height = max(20, round(region.height * 0.16))
    max_height = max(min_height, round(region.height * 0.98))
    min_cells = max(40, (min_width // sample_step) * (min_height // sample_step) // 5)

    for start in range(len(mask)):
        if not mask[start] or visited[start]:
            continue

        stack = [start]
        visited[start] = 1
        min_column = max_column = start % columns
        min_row = max_row = start // columns
        cells = 0

        while stack:
            current = stack.pop()
            row, column = divmod(current, columns)
            cells += 1
            min_column = min(min_column, column)
            max_column = max(max_column, column)
            min_row = min(min_row, row)
            max_row = max(max_row, row)

            if column > 0:
                neighbor = current - 1
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if column + 1 < columns:
                neighbor = current + 1
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if row > 0:
                neighbor = current - columns
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if row + 1 < rows:
                neighbor = current + columns
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)

        if cells < min_cells:
            continue

        left = min_column * sample_step
        top = min_row * sample_step
        right = min(region.width, (max_column + 1) * sample_step)
        bottom = min(region.height, (max_row + 1) * sample_step)
        width = right - left
        height = bottom - top
        if not min_width <= width <= max_width:
            continue
        if not min_height <= height <= max_height:
            continue

        sampled_width = max_column - min_column + 1
        sampled_height = max_row - min_row + 1
        density = cells / (sampled_width * sampled_height)
        if density < 0.20:
            continue

        local_rect = PixelRect(left, top, width, height)
        source = region.normalized_rect
        normalized_rect = NormalizedRect(
            source.left + source.width * (left / region.width),
            source.top + source.height * (top / region.height),
            source.width * (width / region.width),
            source.height * (height / region.height),
        )
        candidates.append(CardFaceLocation(local_rect, normalized_rect, density))

    return sorted(candidates, key=lambda candidate: candidate.center.x)


def _serialize(locations: list[CardFaceLocation]) -> dict:
    return {
        "count": len(locations),
        "cards": [
            {
                "index": index,
                "center": {"x": location.center.x, "y": location.center.y},
                "density": location.density,
                "local_rect": {
                    "left": location.local_rect.left,
                    "top": location.local_rect.top,
                    "width": location.local_rect.width,
                    "height": location.local_rect.height,
                },
                "normalized_rect": {
                    "left": location.normalized_rect.left,
                    "top": location.normalized_rect.top,
                    "width": location.normalized_rect.width,
                    "height": location.normalized_rect.height,
                },
            }
            for index, location in enumerate(locations)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locate visible playing-card faces in a live Steam Balatro hand."
    )
    parser.add_argument("--templates", default="balatro-phase-templates.json")
    parser.add_argument("--output", default="balatro-card-locator.json")
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    parser.add_argument("--sample-step", type=int, default=2)
    parser.add_argument("--min-brightness", type=int, default=165)
    parser.add_argument("--max-channel-spread", type=int, default=70)
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
            "card location requires SELECTING_HAND, got "
            f"{observation.phase.phase}"
        )

    hand = BalatroViewport(observation.frame).crop(DEFAULT_HAND_REGION)
    locations = locate_card_faces(
        hand,
        sample_step=args.sample_step,
        min_brightness=args.min_brightness,
        max_channel_spread=args.max_channel_spread,
    )
    result = _serialize(locations)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Located card-face candidates: {len(locations)}")
    for index, location in enumerate(locations):
        print(
            f"{index}: center=({location.center.x:.4f}, {location.center.y:.4f}) "
            f"rect=({location.normalized_rect.left:.4f}, "
            f"{location.normalized_rect.top:.4f}, "
            f"{location.normalized_rect.width:.4f}, "
            f"{location.normalized_rect.height:.4f}) "
            f"density={location.density:.3f}"
        )
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
