from games.balatro.live.external.card_locator import CardFaceLocation
from games.balatro.live.external.expected_card_locator import (
    _locations_form_uniform_grid,
    locate_card_faces_expected_count,
)
from games.balatro.live.external.viewport import FrameRegion, NormalizedRect, PixelRect


def _frame_region(width, height, pixels):
    return FrameRegion(
        normalized_rect=NormalizedRect(0.10, 0.50, 0.80, 0.40),
        pixel_rect=PixelRect(40, 100, width, height),
        width=width,
        height=height,
        bgra=bytes(pixels),
    )


def _fill(pixels, width, left, top, rect_width, rect_height, value=230):
    pixel = bytes((value, value, value, 255))
    for y in range(top, top + rect_height):
        for x in range(left, left + rect_width):
            index = (y * width + x) * 4
            pixels[index : index + 4] = pixel


def _anchored_hand_region(*, visible_indices):
    width = 500
    height = 240
    pixels = bytearray(b"\x20\x50\x20\xff" * (width * height))
    for index in range(8):
        value = 230 if index in visible_indices else 90
        _fill(pixels, width, 20 + index * 48, 70, 30, 90, value)
    return _frame_region(width, height, pixels)


def _location(x):
    rect = NormalizedRect(x - 0.02, 0.65, 0.04, 0.10)
    return CardFaceLocation(
        local_rect=PixelRect(round(x * 1000), 50, 40, 100),
        normalized_rect=rect,
        density=1.0,
    )


def test_expected_count_locator_reconstructs_internal_dimmed_cards_from_grid():
    region = _anchored_hand_region(visible_indices={0, 1, 3, 4, 5, 7})

    cards = locate_card_faces_expected_count(region, 8)

    assert len(cards) == 8
    assert [card.local_rect.center.x for card in cards] == [
        35,
        83,
        131,
        179,
        227,
        275,
        323,
        371,
    ]


def test_expected_count_locator_fails_closed_when_grid_position_is_ambiguous():
    region = _anchored_hand_region(visible_indices={1, 2, 3, 4})

    cards = locate_card_faces_expected_count(region, 8)

    assert len(cards) != 8


def test_exact_count_requires_uniform_horizontal_spacing():
    uniform = [_location(0.15 + index * 0.08) for index in range(8)]
    distorted = [
        _location(x)
        for x in (0.1682, 0.2242, 0.3205, 0.4077, 0.4948, 0.5820, 0.6692, 0.7564)
    ]

    assert _locations_form_uniform_grid(uniform) is True
    assert _locations_form_uniform_grid(distorted) is False
