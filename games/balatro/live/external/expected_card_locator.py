from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .card_locator import (
    CARD_FACE_STRIDE_HEIGHT_RATIO,
    MAX_HAND_CARDS,
    CardComponentDiagnostic,
    CardFaceLocation,
    inspect_card_face_components,
    locate_card_faces,
)
from .viewport import FrameRegion, NormalizedRect, PixelRect


DEFAULT_PROFILES = (
    (165, 70),
    (150, 85),
    (140, 100),
    (130, 115),
    (120, 130),
)


@dataclass(frozen=True)
class _GridFit:
    start_x: float
    stride: float
    top: float
    card_width: float
    card_height: float
    score: float
    mapped_indices: tuple[int, ...]


def locate_card_faces_expected_count(
    region: FrameRegion,
    expected_count: int,
    *,
    profiles=DEFAULT_PROFILES,
) -> list[CardFaceLocation]:
    """Locate a hand with a strict save-backed expected card count.

    Normal bright-card detection is always preferred. If dimmed cards make that
    impossible, individually accepted card components are used as anchors for an
    evenly spaced Balatro hand grid. A reconstructed grid is returned only when it
    is unambiguous and every anchor agrees with it. Otherwise the first ordinary
    locator result is returned so the caller's exact-count guard fails closed.
    """

    if not 1 <= expected_count <= MAX_HAND_CARDS:
        raise ValueError(
            f"expected_count must be between 1 and {MAX_HAND_CARDS}, got {expected_count}"
        )

    first_locations: list[CardFaceLocation] | None = None
    fits: list[_GridFit] = []

    for min_brightness, max_channel_spread in profiles:
        locations = locate_card_faces(
            region,
            min_brightness=min_brightness,
            max_channel_spread=max_channel_spread,
        )
        if first_locations is None:
            first_locations = locations
        if len(locations) == expected_count:
            return locations

        diagnostics = inspect_card_face_components(
            region,
            min_brightness=min_brightness,
            max_channel_spread=max_channel_spread,
        )
        fit = _fit_grid_from_accepted_components(diagnostics, expected_count)
        if fit is not None:
            fits.append(fit)

    chosen = _choose_unambiguous_fit(fits)
    if chosen is not None:
        return _locations_from_fit(region, chosen, expected_count)

    return first_locations or []


def _fit_grid_from_accepted_components(
    diagnostics: list[CardComponentDiagnostic],
    expected_count: int,
) -> _GridFit | None:
    accepted = [component for component in diagnostics if component.accepted]
    row = _dominant_row(accepted)
    minimum_anchors = max(4, expected_count // 2)
    if len(row) < minimum_anchors:
        return None

    anchors = sorted(row, key=lambda component: component.local_rect.center.x)
    heights = [component.local_rect.height for component in anchors]
    widths = [component.local_rect.width for component in anchors]
    tops = [component.local_rect.top for component in anchors]
    card_height = float(median(heights))
    card_width = float(median(widths))
    top = float(median(tops))
    target_stride = card_height * CARD_FACE_STRIDE_HEIGHT_RATIO
    tolerance = max(3.0, card_height * 0.16)
    centers = [component.local_rect.center.x for component in anchors]

    candidates: list[_GridFit] = []
    for left_index in range(len(centers) - 1):
        for right_index in range(left_index + 1, len(centers)):
            delta = centers[right_index] - centers[left_index]
            if delta <= 0:
                continue
            for grid_gap in range(1, expected_count):
                stride = delta / grid_gap
                stride_ratio = stride / card_height
                if not 0.38 <= stride_ratio <= 0.68:
                    continue

                for anchor_grid_index in range(expected_count):
                    start_x = centers[left_index] - anchor_grid_index * stride
                    mapped: list[int] = []
                    residual = 0.0
                    valid = True
                    for center in centers:
                        raw_index = (center - start_x) / stride
                        grid_index = int(round(raw_index))
                        if not 0 <= grid_index < expected_count:
                            valid = False
                            break
                        expected_x = start_x + grid_index * stride
                        error = abs(center - expected_x)
                        if error > tolerance:
                            valid = False
                            break
                        mapped.append(grid_index)
                        residual += error

                    if not valid or len(set(mapped)) != len(mapped):
                        continue
                    if max(mapped) - min(mapped) < max(2, expected_count - 3):
                        continue

                    score = residual
                    score += abs(stride - target_stride) * len(centers) * 0.20
                    candidates.append(
                        _GridFit(
                            start_x=start_x,
                            stride=stride,
                            top=top,
                            card_width=card_width,
                            card_height=card_height,
                            score=score,
                            mapped_indices=tuple(mapped),
                        )
                    )

    if not candidates:
        return None

    candidates.sort(key=lambda fit: fit.score)
    best = candidates[0]
    for alternative in candidates[1:]:
        if _equivalent_fit(best, alternative):
            continue
        if alternative.score <= best.score + max(1.0, card_height * 0.03):
            return None
        break
    return best


def _dominant_row(
    components: list[CardComponentDiagnostic],
) -> list[CardComponentDiagnostic]:
    if not components:
        return []

    ordered = sorted(components, key=lambda component: component.cells, reverse=True)
    best_group: list[CardComponentDiagnostic] = []
    best_cells = -1
    for seed in ordered:
        seed_rect = seed.local_rect
        tolerance = max(4.0, seed_rect.height * 0.30)
        group = [
            component
            for component in components
            if abs(component.local_rect.center.y - seed_rect.center.y) <= tolerance
        ]
        cells = sum(component.cells for component in group)
        if len(group) > len(best_group) or (
            len(group) == len(best_group) and cells > best_cells
        ):
            best_group = group
            best_cells = cells
    return best_group


def _choose_unambiguous_fit(fits: list[_GridFit]) -> _GridFit | None:
    if not fits:
        return None
    fits = sorted(fits, key=lambda fit: fit.score)
    best = fits[0]
    for alternative in fits[1:]:
        if _equivalent_fit(best, alternative):
            continue
        if alternative.score <= best.score + max(1.0, best.card_height * 0.03):
            return None
        break
    return best


def _equivalent_fit(first: _GridFit, second: _GridFit) -> bool:
    tolerance = max(2.0, min(first.card_height, second.card_height) * 0.08)
    return (
        abs(first.start_x - second.start_x) <= tolerance
        and abs(first.stride - second.stride) <= tolerance * 0.5
    )


def _locations_from_fit(
    region: FrameRegion,
    fit: _GridFit,
    count: int,
) -> list[CardFaceLocation]:
    width = max(1, round(fit.card_width))
    height = max(1, round(fit.card_height))
    top = round(fit.top)
    locations: list[CardFaceLocation] = []

    for index in range(count):
        center_x = fit.start_x + index * fit.stride
        left = round(center_x - width / 2)
        rect = PixelRect(left, top, width, height)
        if (
            rect.left < 0
            or rect.top < 0
            or rect.left + rect.width > region.width
            or rect.top + rect.height > region.height
        ):
            return []
        locations.append(_location_from_rect(region, rect))
    return locations


def _location_from_rect(region: FrameRegion, rect: PixelRect) -> CardFaceLocation:
    source = region.normalized_rect
    normalized_rect = NormalizedRect(
        source.left + source.width * (rect.left / region.width),
        source.top + source.height * (rect.top / region.height),
        source.width * (rect.width / region.width),
        source.height * (rect.height / region.height),
    )
    return CardFaceLocation(rect, normalized_rect, 0.0)
