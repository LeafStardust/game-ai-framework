from __future__ import annotations

from dataclasses import dataclass

from .card_aligned_features import detect_card_face_top
from .card_templates import RGBImage
from .viewport import BalatroViewport


@dataclass(frozen=True)
class HouseCardVisibility:
    """Public screen visibility for one located card under The House."""

    index: int
    face_up: bool


def _rgb_image_from_bgra(width: int, height: int, bgra: bytes) -> RGBImage:
    rgb = bytearray(width * height * 3)
    destination = 0
    for offset in range(0, len(bgra), 4):
        blue, green, red = bgra[offset : offset + 3]
        rgb[destination : destination + 3] = bytes((red, green, blue))
        destination += 3
    return RGBImage(width, height, bytes(rgb))


def is_face_up_image(image: RGBImage) -> bool:
    """Return whether a card image visibly exposes the normal neutral face.

    The existing aligned-card feature detector searches the unoccluded left side
    of a Balatro card for the bright neutral playing-card face. Card backs do not
    expose that face and therefore fail closed as face-down. This intentionally
    answers visibility only; it never attempts to infer a hidden rank or suit.
    """

    try:
        detect_card_face_top(image)
    except ValueError:
        return False
    return True


def classify_house_card_visibility(frame, locations) -> tuple[HouseCardVisibility, ...]:
    """Classify located hand cards from the captured screen only."""

    viewport = BalatroViewport(frame)
    result = []
    for index, location in enumerate(locations):
        region = viewport.crop(location.normalized_rect)
        image = _rgb_image_from_bgra(region.width, region.height, region.bgra)
        result.append(HouseCardVisibility(index, is_face_up_image(image)))
    return tuple(result)
