import pytest

from games.balatro.live.external.card_locator import locate_card_faces
from games.balatro.live.external.viewport import FrameRegion, NormalizedRect, PixelRect


def _region(width=400, height=200):
    pixels = bytearray(b"\x20\x50\x20\xff" * (width * height))

    def fill(left, top, rect_width, rect_height, pixel=b"\xe6\xe6\xe6\xff"):
        for y in range(top, top + rect_height):
            for x in range(left, left + rect_width):
                index = (y * width + x) * 4
                pixels[index : index + 4] = pixel

    for index in range(8):
        fill(10 + index * 47, 80, 30, 90)
    fill(390, 10, 5, 5)

    return FrameRegion(
        normalized_rect=NormalizedRect(0.10, 0.50, 0.80, 0.40),
        pixel_rect=PixelRect(40, 100, width, height),
        width=width,
        height=height,
        bgra=bytes(pixels),
    )


def test_locate_card_faces_finds_ordered_bright_card_regions():
    cards = locate_card_faces(_region(), sample_step=1)

    assert len(cards) == 8
    assert [card.local_rect.left for card in cards] == [
        10,
        57,
        104,
        151,
        198,
        245,
        292,
        339,
    ]
    assert all(card.density == pytest.approx(1.0) for card in cards)
    assert [card.center.x for card in cards] == sorted(card.center.x for card in cards)


def test_locate_card_faces_maps_locations_back_to_full_viewport():
    first = locate_card_faces(_region(), sample_step=1)[0]

    assert first.normalized_rect.left == pytest.approx(0.12)
    assert first.normalized_rect.top == pytest.approx(0.66)
    assert first.normalized_rect.width == pytest.approx(0.06)
    assert first.normalized_rect.height == pytest.approx(0.18)
    assert first.center.x == pytest.approx(0.15)
    assert first.center.y == pytest.approx(0.75)


def test_locate_card_faces_rejects_invalid_threshold_settings():
    region = _region()

    with pytest.raises(ValueError, match="sample_step"):
        locate_card_faces(region, sample_step=0)

    with pytest.raises(ValueError, match="min_brightness"):
        locate_card_faces(region, min_brightness=300)

    with pytest.raises(ValueError, match="max_channel_spread"):
        locate_card_faces(region, max_channel_spread=-1)
