from __future__ import annotations

from dataclasses import dataclass

from .card_locator import (
    MAX_HAND_CARDS,
    CardFaceLocation,
    inspect_card_face_components,
    locate_card_faces,
)
from .expected_card_locator import DEFAULT_PROFILES, _locations_form_uniform_grid
from .viewport import FrameRegion, NormalizedRect, PixelRect


CARD_FACE_WIDTH_HEIGHT_RATIO = 0.67
MIN_STRIDE_HEIGHT_RATIO = 0.38
MAX_STRIDE_HEIGHT_RATIO = 0.68


@dataclass(frozen=True)
class _WideHandCandidate:
    left: float
    top: float
    width: float
    height: float
    density: float
    card_width: float
    stride: float

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2.0



def locate_head_card_faces(
    region: FrameRegion,
    expected_count: int,
    *,
    profiles=DEFAULT_PROFILES,
) -> list[CardFaceLocation]:
    """Locate The Head's dimmed hand using a save-backed card count.

    First accept an ordinary exact-count result only when it already forms a
    uniform resting grid. Otherwise collect physically plausible wide hand blobs
    across brightness profiles, group repeated observations of the same row, and
    reconstruct exactly ``expected_count`` slots from the widest observation in
    the uniquely dominant row family.

    The function fails closed by returning a non-matching count when the wide
    observations are absent or ambiguous.
    """

    if not 1 <= expected_count <= MAX_HAND_CARDS:
        raise ValueError(
            f"expected_count must be between 1 and {MAX_HAND_CARDS}, got {expected_count}"
        )

    first_locations: list[CardFaceLocation] | None = None
    candidates: list[_WideHandCandidate] = []

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
        for component in diagnostics:
            if component.rejection != "too_wide" or component.density < 0.30:
                continue
            candidate = _candidate_from_component(component.local_rect, component.density, expected_count)
            if candidate is not None:
                candidates.append(candidate)

    chosen = _choose_dominant_family(candidates)
    if chosen is not None:
        locations = _locations_from_candidate(region, chosen, expected_count)
        if len(locations) == expected_count and _locations_form_uniform_grid(locations):
            return locations

    if first_locations is not None and len(first_locations) != expected_count:
        return first_locations
    return []



def _candidate_from_component(
    rect: PixelRect,
    density: float,
    expected_count: int,
) -> _WideHandCandidate | None:
    if expected_count < 2 or rect.height <= 0:
        return None

    height = float(rect.height)
    card_width = height * CARD_FACE_WIDTH_HEIGHT_RATIO
    if rect.width <= card_width:
        return None

    stride = (float(rect.width) - card_width) / (expected_count - 1)
    stride_ratio = stride / height
    if not MIN_STRIDE_HEIGHT_RATIO <= stride_ratio <= MAX_STRIDE_HEIGHT_RATIO:
        return None

    return _WideHandCandidate(
        left=float(rect.left),
        top=float(rect.top),
        width=float(rect.width),
        height=height,
        density=float(density),
        card_width=card_width,
        stride=stride,
    )



def _same_row_family(first: _WideHandCandidate, second: _WideHandCandidate) -> bool:
    reference_height = min(first.height, second.height)
    if reference_height <= 0:
        return False
    if abs(first.center_y - second.center_y) > reference_height * 0.18:
        return False
    if abs(first.height - second.height) > reference_height * 0.20:
        return False
    return True



def _choose_dominant_family(
    candidates: list[_WideHandCandidate],
) -> _WideHandCandidate | None:
    if not candidates:
        return None

    families: list[list[_WideHandCandidate]] = []
    for candidate in candidates:
        matching = next(
            (
                family
                for family in families
                if _same_row_family(candidate, family[0])
            ),
            None,
        )
        if matching is None:
            families.append([candidate])
        else:
            matching.append(candidate)

    families.sort(
        key=lambda family: (
            len(family),
            max(candidate.width for candidate in family),
        ),
        reverse=True,
    )
    best_family = families[0]

    # Repeated observations across threshold profiles are the safety signal. A
    # one-off blob is not enough when another row family is similarly supported.
    if len(families) > 1 and len(families[1]) == len(best_family):
        return None

    return max(
        best_family,
        key=lambda candidate: (candidate.width, candidate.density),
    )



def _locations_from_candidate(
    region: FrameRegion,
    candidate: _WideHandCandidate,
    expected_count: int,
) -> list[CardFaceLocation]:
    width = max(1, round(candidate.card_width))
    height = max(1, round(candidate.height))
    top = round(candidate.top)
    start_center = candidate.left + candidate.card_width / 2.0
    locations: list[CardFaceLocation] = []

    for index in range(expected_count):
        center_x = start_center + index * candidate.stride
        left = round(center_x - width / 2.0)
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
