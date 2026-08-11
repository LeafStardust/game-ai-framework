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

    Normal bright-card detection is preferred only when its returned centers form
    a plausible evenly-spaced Balatro hand grid. If dimmed cards or mixed
    individual/wide components distort that result, the locator reconstructs a
    uniform grid from either a dominant wide hand component or individually
    accepted card anchors. A reconstructed grid is returned only when the fit is
    unambiguous; otherwise the caller's exact-count guard fails closed.
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
        if len(locations) == expected_count and _locations_form_uniform_grid(locations):
            return locations

        diagnostics = inspect_card_face_components(
            region,
            min_brightness=min_brightness,
            max_channel_spread=max_channel_spread,
        )

        wide_fit = _fit_grid_from_wide_component(diagnostics, expected_count)
        if wide_fit is not None:
            fits.append(wide_fit)

        anchor_fit = _fit_grid_from_accepted_components(diagnostics, expected_count)
        if anchor_fit is not None:
            fits.append(anchor_fit)

    chosen = _choose_unambiguous_fit(fits)
    if chosen is not None:
        locations = _locations_from_fit(region, chosen, expected_count)
        if _locations_form_uniform_grid(locations):
            return locations

    # Preserve diagnostic information only when it still guarantees that the
    # caller's strict count check will fail. Never return an exact-count result
    # whose geometry has already been rejected as malformed.
    if first_locations is not None and len(first_locations) != expected_count:
        return first_locations
    return []


def _locations_form_uniform_grid(locations: list[CardFaceLocation]) -> bool:
    if len(locations) <= 2:
        return True

    ordered = sorted(locations, key=lambda location: location.center.x)
    gaps = [
        ordered[index + 1].center.x - ordered[index].center.x
        for index in range(len(ordered) - 1)
    ]
    if any(gap <= 0 for gap in gaps):
        return False

    typical_gap = median(gaps)
    if typical_gap <= 0:
        return False

    # Real Balatro card rows are effectively uniform. Keep enough tolerance for
    # pixel quantization while rejecting mixed component/split results such as
    # 0.056, 0.096, 0.087, ... that can still accidentally total the save count.
    if any(abs(gap - typical_gap) > typical_gap * 0.20 for gap in gaps):
        return False

    return True


def _fit_grid_from_wide_component(
    diagnostics: list[CardComponentDiagnostic],
    expected_count: int,
) -> _GridFit | None:
    """Split a dominant connected hand blob using the authoritative card count.

    Under suit-debuff Boss Blinds, lowering the brightness threshold can connect
    the entire overlapping hand into one wide component. The generic card locator
    must infer a count from nominal stride and can over-split that blob. Here the
    save already supplies the exact visible hand count, so derive the only uniform
    card grid consistent with that count and reject components whose resulting
    stride is not physically plausible for a Balatro hand.
    """

    if expected_count < 2:
        return None

    wide_components = [
        component
        for component in diagnostics
        if component.rejection == "too_wide" and component.density >= 0.30
    ]
    if not wide_components:
        return None

    candidates: list[_GridFit] = []
    for component in wide_components:
        rect = component.local_rect
        card_height = float(rect.height)
        if card_height <= 0:
            continue

        # Match the card-face geometry used by the ordinary wide-component
        # splitter, but use the authoritative count rather than inferring count.
        card_width = card_height * 0.67
        if rect.width <= card_width:
            continue

        stride = (float(rect.width) - card_width) / (expected_count - 1)
        stride_ratio = stride / card_height
        if not 0.38 <= stride_ratio <= 0.68:
            continue

        start_x = float(rect.left) + card_width / 2.0
        fit = _GridFit(
            start_x=start_x,
            stride=stride,
            top=float(rect.top),
            card_width=card_width,
            card_height=card_height,
            # Prefer dense, large hand blobs and a stride near Balatro's nominal
            # overlap geometry. Small partial blobs naturally fail the ratio gate.
            score=(
                abs(stride - card_height * CARD_FACE_STRIDE_HEIGHT_RATIO)
                + (1.0 - min(1.0, component.density)) * card_height * 0.10
            ),
            mapped_indices=tuple(range(expected_count)),
        )
        candidates.append(fit)

    if not candidates:
        return None

    candidates.sort(key=lambda fit: fit.score)
    best = candidates[0]
    for alternative in candidates[1:]:
        if _equivalent_fit(best, alternative):
            continue
        if alternative.score <= best.score + max(1.0, best.card_height * 0.03):
            return None
        break
    return best


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
