from games.balatro.live.external.card_templates import RGBImage
from games.balatro.live.external.hud_digit_templates import (
    HudDigitTemplate,
    HudDigitTemplateSet,
)
from games.balatro.live.external.hud_digits import (
    DIGIT_COLUMNS,
    DIGIT_ROWS,
    extract_hud_digit_signatures,
)
from games.balatro.live.external.hud_recognition import (
    recognize_hud_digit,
    recognize_hud_number,
    rgb_image_from_bgra,
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


def test_recognize_hud_digit_reports_runner_up_margin():
    zero = (0,) * (DIGIT_COLUMNS * DIGIT_ROWS)
    one = (255,) * (DIGIT_COLUMNS * DIGIT_ROWS)
    templates = HudDigitTemplateSet(
        DIGIT_COLUMNS,
        DIGIT_ROWS,
        (
            HudDigitTemplate("0", zero),
            HudDigitTemplate("1", one),
        ),
    )

    match = recognize_hud_digit(zero, templates)

    assert match.digit == "0"
    assert match.distance == 0.0
    assert match.runner_up == "1"
    assert match.margin == 1.0


def test_recognize_hud_number_composes_matched_digits():
    image = _image(
        70,
        40,
        [(5, 7, 17, 34), (27, 7, 42, 34)],
        (255, 76, 64),
    )
    signatures = extract_hud_digit_signatures(image, "blind_target")
    templates = HudDigitTemplateSet(
        DIGIT_COLUMNS,
        DIGIT_ROWS,
        (
            HudDigitTemplate("3", signatures[0]),
            HudDigitTemplate("0", signatures[1]),
        ),
    )

    recognition = recognize_hud_number(image, "blind_target", templates)

    assert recognition.value == 30
    assert [match.digit for match in recognition.digits] == ["3", "0"]


def test_rgb_image_from_bgra_converts_channel_order():
    image = rgb_image_from_bgra(1, 1, bytes((3, 2, 1, 255)))

    assert image == RGBImage(1, 1, bytes((1, 2, 3)))
