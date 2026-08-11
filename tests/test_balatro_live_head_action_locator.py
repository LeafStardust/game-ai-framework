from games.balatro.live.external.expected_card_locator import _locations_form_uniform_grid
from games.balatro.live.external.head_blind_planner_action_live_validation import (
    _head_card_locator,
)
from games.balatro.live.external.viewport import FrameRegion, NormalizedRect, PixelRect


def _frame_region(width, height, pixels):
    return FrameRegion(
        normalized_rect=NormalizedRect(0.15, 0.50, 0.84, 0.49),
        pixel_rect=PixelRect(0, 0, width, height),
        width=width,
        height=height,
        bgra=bytes(pixels),
    )


def _fill(pixels, width, left, top, rect_width, rect_height, value=150):
    pixel = bytes((value, value, value, 255))
    for y in range(top, top + rect_height):
        for x in range(left, left + rect_width):
            index = (y * width + x) * 4
            pixels[index : index + 4] = pixel


def test_head_executor_locator_uses_uniform_expected_count_grid():
    width = 1280
    height = 480
    pixels = bytearray(b"\x20\x50\x20\xff" * (width * height))

    # Reproduce the live failure class: one connected overlapping hand blob whose
    # ordinary face locator can infer the wrong number of cards.
    _fill(pixels, width, 174, 84, 842, 178, value=145)
    region = _frame_region(width, height, pixels)

    locations = _head_card_locator(8)(region)

    assert len(locations) == 8
    assert _locations_form_uniform_grid(locations) is True
    assert len({round(location.center.y, 6) for location in locations}) == 1
