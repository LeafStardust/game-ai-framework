import pytest

from games.balatro.live.external.card_templates import RGBImage
from games.balatro.live.external.hud_digits import (
    extract_hud_digit_signatures,
    signature_distance,
)


def _image(width, height, components, color):
    background = (46, 58, 60)
    pixels = [background] * (width * height)
    for left, top, right, bottom in components:
        for y in range(top, bottom):
            for x in range(left, right):
                pixels[y * width + x] = color
    return RGBImage(
        width,
        height,
        bytes(channel for pixel in pixels for channel in pixel),
    )


def test_digit_signature_is_color_invariant_across_hud_fields():
    shape = [(10, 8, 15, 32), (5, 20, 20, 25)]
    red = _image(30, 40, shape, (255, 76, 64))
    blue = _image(30, 40, shape, (0, 147, 255))

    red_signature = extract_hud_digit_signatures(red, "discards")
    blue_signature = extract_hud_digit_signatures(blue, "hands")

    assert red_signature == blue_signature


def test_money_skips_currency_prefix_component():
    image = _image(
        60,
        40,
        [
            (5, 7, 15, 34),
            (25, 7, 38, 34),
        ],
        (245, 178, 68),
    )

    signatures = extract_hud_digit_signatures(
        image,
        "money",
        expected_digits=1,
    )

    assert len(signatures) == 1


def test_score_skips_chip_prefix_component():
    image = _image(
        60,
        40,
        [
            (2, 7, 13, 34),
            (25, 7, 38, 34),
        ],
        (255, 255, 255),
    )

    signatures = extract_hud_digit_signatures(
        image,
        "score",
        expected_digits=1,
    )

    assert len(signatures) == 1


def test_digit_extraction_rejects_unexpected_component_count():
    image = _image(40, 40, [(10, 7, 22, 34)], (255, 76, 64))

    with pytest.raises(ValueError, match="expected 2 digit components"):
        extract_hud_digit_signatures(
            image,
            "blind_target",
            expected_digits=2,
        )


def test_signature_distance_requires_matching_nonempty_signatures():
    assert signature_distance((0, 255), (0, 255)) == 0.0
    assert signature_distance((0, 255), (255, 0)) == 1.0

    with pytest.raises(ValueError, match="equal dimensions"):
        signature_distance((0,), (0, 1))
    with pytest.raises(ValueError, match="cannot be empty"):
        signature_distance((), ())
