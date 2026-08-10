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


@dataclass(frozen=True)
class CardComponentDiagnostic:
    local_rect: PixelRect
    cells: int
    density: float
    rejection: str | None

    @property
    def accepted(self) -> bool:
        return self.rejection is None


def inspect_card_face_components(
    region: FrameRegion,
    *,
    sample_step: int = 2,
    min_brightness: int = 165,
    max_channel_spread: int = 70,
) -> list[CardComponentDiagnostic]:
    _validate_settings(sample_step, min_brightness, max_channel_spread)
    mask, columns, rows = _build_bright_mask(
        region,
        sample_step,
        min_brightness,
        max_channel_spread,
    )
    min_width = max(12, round(region.width * 0.025))
    max_width = max(min_width, round(region.width * 0.18))
    min_height = max(20, round(region.height * 0.16))
    max_height = max(min_height, round(region.height * 0.98))
    min_cells = max(
        40,
        (min_width // sample_step) * (min_height // sample_step) // 5,
    )
    report_floor = max(8, min_cells // 4)
    visited = bytearray(len(mask))
    diagnostics: list[CardComponentDiagnostic] = []

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

        if cells < report_floor:
            continue

        left = min_column * sample_step
        top = min_row * sample_step
        right = min(region.width, (max_column + 1) * sample_step)
        bottom = min(region.height, (max_row + 1) * sample_step)
        width = right - left
        height = bottom - top
        sampled_width = max_column - min_column + 1
        sampled_height = max_row - min_row + 1
        density = cells / (sampled_width * sampled_height)
        rejection = _rejection_reason(
            cells,
            width,
            height,
            density,
            min_cells=min_cells,
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
        )
        diagnostics.append(
            CardComponentDiagnostic(
                PixelRect(left, top, width, height),
                cells,
                density,
                rejection,
            )
        )

    return sorted(diagnostics, key=lambda item: item.cells, reverse=True)


def locate_card_faces(
    region: FrameRegion,
    *,
    sample_step: int = 2,
    min_brightness: int = 165,
    max_channel_spread: int = 70,
) -> list[CardFaceLocation]:
    diagnostics = inspect_card_face_components(
        region,
        sample_step=sample_step,
        min_brightness=min_brightness,
        max_channel_spread=max_channel_spread,
    )
    candidates = [
        _location_from_component(region, component)
        for component in diagnostics
        if component.accepted
    ]
    return sorted(candidates, key=lambda candidate: candidate.center.x)


def _build_bright_mask(
    region: FrameRegion,
    sample_step: int,
    min_brightness: int,
    max_channel_spread: int,
) -> tuple[bytearray, int, int]:
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

    return mask, columns, rows


def _rejection_reason(
    cells: int,
    width: int,
    height: int,
    density: float,
    *,
    min_cells: int,
    min_width: int,
    max_width: int,
    min_height: int,
    max_height: int,
) -> str | None:
    if cells < min_cells:
        return "too_few_bright_samples"
    if width < min_width:
        return "too_narrow"
    if width > max_width:
        return "too_wide"
    if height < min_height:
        return "too_short"
    if height > max_height:
        return "too_tall"
    if density < 0.20:
        return "too_sparse"
    return None


def _location_from_component(
    region: FrameRegion,
    component: CardComponentDiagnostic,
) -> CardFaceLocation:
    rect = component.local_rect
    source = region.normalized_rect
    normalized_rect = NormalizedRect(
        source.left + source.width * (rect.left / region.width),
        source.top + source.height * (rect.top / region.height),
        source.width * (rect.width / region.width),
        source.height * (rect.height / region.height),
    )
    return CardFaceLocation(rect, normalized_rect, component.density)


def _validate_settings(
    sample_step: int,
    min_brightness: int,
    max_channel_spread: int,
) -> None:
    if sample_step < 1:
        raise ValueError("sample_step must be positive")
    if not 0 <= min_brightness <= 255:
        raise ValueError("min_brightness must be between 0 and 255")
    if not 0 <= max_channel_spread <= 255:
        raise ValueError("max_channel_spread must be between 0 and 255")


def _serialize(
    locations: list[CardFaceLocation],
    diagnostics: list[CardComponentDiagnostic],
) -> dict:
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
        "components": [
            {
                "accepted": component.accepted,
                "cells": component.cells,
                "density": component.density,
                "rejection": component.rejection,
                "local_rect": {
                    "left": component.local_rect.left,
                    "top": component.local_rect.top,
                    "width": component.local_rect.width,
                    "height": component.local_rect.height,
                },
            }
            for component in diagnostics
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
    diagnostics = inspect_card_face_components(
        hand,
        sample_step=args.sample_step,
        min_brightness=args.min_brightness,
        max_channel_spread=args.max_channel_spread,
    )
    locations = [
        _location_from_component(hand, component)
        for component in diagnostics
        if component.accepted
    ]
    locations.sort(key=lambda location: location.center.x)
    result = _serialize(locations, diagnostics)
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

    rejected = [component for component in diagnostics if not component.accepted]
    print(f"Rejected substantial components: {len(rejected)}")
    for index, component in enumerate(rejected[:12]):
        rect = component.local_rect
        print(
            f"R{index}: reason={component.rejection} "
            f"rect=({rect.left}, {rect.top}, {rect.width}, {rect.height}) "
            f"cells={component.cells} density={component.density:.3f}"
        )
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
