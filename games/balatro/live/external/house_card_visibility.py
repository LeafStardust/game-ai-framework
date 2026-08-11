from __future__ import annotations

from dataclasses import dataclass

from .card_aligned_features import detect_card_face_top
from .card_templates import RGBImage
from .viewport import BalatroViewport


FACE_INTERIOR_LEFT = 0.12
FACE_INTERIOR_RIGHT = 0.58
FACE_INTERIOR_TOP_OFFSET = 0.08
FACE_INTERIOR_BOTTOM_OFFSET = 0.44
FACE_NEUTRAL_MIN = 170
FACE_NEUTRAL_CHROMA_MAX = 45
FACE_INTERIOR_NEUTRAL_FRACTION_MIN = 0.55


@dataclass(frozen=True)
class HouseCardVisibility:
    """Public screen visibility for one located card under The House."""

    index: int
    face_up: bool
    neutral_fraction: float


def _rgb_image_from_bgra(width: int, height: int, bgra: bytes) -> RGBImage:
    rgb = bytearray(width * height * 3)
    destination = 0
    for offset in range(0, len(bgra), 4):
        blue, green, red = bgra[offset : offset + 3]
        rgb[destination : destination + 3] = bytes((red, green, blue))
        destination += 3
    return RGBImage(width, height, bytes(rgb))


def _pixel_rgb(image: RGBImage, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * image.width + x) * 3
    red, green, blue = image.rgb[offset : offset + 3]
    return red, green, blue


def face_interior_neutral_fraction(image: RGBImage) -> float:
    """Measure the bright neutral interior exposed by a normal card face.

    The House card back can contain a bright neutral border, so merely finding a
    white row is not sufficient to establish that rank/suit information is public.
    A face-up Balatro card exposes a broad cream/white interior on its unoccluded
    left side; a card back does not. The measurement intentionally ignores rank
    and suit glyph identity and uses screen pixels only.
    """

    try:
        face_top = detect_card_face_top(image)
    except ValueError:
        return 0.0

    left = max(0, round(FACE_INTERIOR_LEFT * image.width))
    right = min(
        image.width,
        max(left + 1, round(FACE_INTERIOR_RIGHT * image.width)),
    )
    top = max(
        0,
        min(
            image.height - 1,
            face_top + round(FACE_INTERIOR_TOP_OFFSET * image.height),
        ),
    )
    bottom = min(
        image.height,
        max(top + 1, face_top + round(FACE_INTERIOR_BOTTOM_OFFSET * image.height)),
    )

    neutral = 0
    total = 0
    for y in range(top, bottom):
        for x in range(left, right):
            red, green, blue = _pixel_rgb(image, x, y)
            total += 1
            if (
                min(red, green, blue) >= FACE_NEUTRAL_MIN
                and max(red, green, blue) - min(red, green, blue)
                <= FACE_NEUTRAL_CHROMA_MAX
            ):
                neutral += 1

    return neutral / max(1, total)


def is_face_up_image(image: RGBImage) -> bool:
    """Return whether screen pixels confidently expose a normal card face."""

    return face_interior_neutral_fraction(image) >= FACE_INTERIOR_NEUTRAL_FRACTION_MIN


def classify_house_card_visibility(frame, locations) -> tuple[HouseCardVisibility, ...]:
    """Classify located hand cards from the captured screen only."""

    viewport = BalatroViewport(frame)
    result = []
    for index, location in enumerate(locations):
        region = viewport.crop(location.normalized_rect)
        image = _rgb_image_from_bgra(region.width, region.height, region.bgra)
        neutral_fraction = face_interior_neutral_fraction(image)
        result.append(
            HouseCardVisibility(
                index,
                neutral_fraction >= FACE_INTERIOR_NEUTRAL_FRACTION_MIN,
                neutral_fraction,
            )
        )
    return tuple(result)
