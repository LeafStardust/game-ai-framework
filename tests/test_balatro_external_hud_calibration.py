from pathlib import Path

import pytest

from games.balatro.live.external.capture import save_bgra_png
from games.balatro.live.external.hud_calibration import (
    calibrate_hud_digits,
    parse_field_value,
)
from games.balatro.live.external.hud_digit_templates import (
    load_hud_digit_templates,
)


def _save_crop(path: Path, width, height, components, color):
    background = (46, 58, 60)
    pixels = [background] * (width * height)
    for left, top, right, bottom in components:
        for y in range(top, bottom):
            for x in range(left, right):
                pixels[y * width + x] = color

    bgra = bytearray()
    for red, green, blue in pixels:
        bgra.extend((blue, green, red, 255))
    save_bgra_png(width, height, bytes(bgra), path)


def test_parse_field_value():
    assert parse_field_value("money=14") == ("money", "14")

    with pytest.raises(ValueError, match="FIELD=INTEGER"):
        parse_field_value("money")
    with pytest.raises(ValueError, match="non-negative integer"):
        parse_field_value("money=-4")


def test_calibration_builds_and_appends_digit_templates(tmp_path):
    prefix = tmp_path / "hud"
    output = tmp_path / "digits.json"

    _save_crop(
        tmp_path / "hud-round.png",
        40,
        40,
        [(10, 7, 22, 34)],
        (255, 143, 0),
    )
    templates = calibrate_hud_digits(
        [("round", "1")],
        input_prefix=prefix,
        output_path=output,
        replace=True,
    )
    assert templates.coverage == {"1"}

    _save_crop(
        tmp_path / "hud-blind_target.png",
        70,
        40,
        [(5, 7, 17, 34), (27, 7, 39, 34)],
        (255, 76, 64),
    )
    templates = calibrate_hud_digits(
        [("blind_target", "30")],
        input_prefix=prefix,
        output_path=output,
    )

    assert templates.coverage == {"0", "1", "3"}
    assert load_hud_digit_templates(output) == templates


def test_calibration_deduplicates_identical_samples(tmp_path):
    prefix = tmp_path / "hud"
    output = tmp_path / "digits.json"
    _save_crop(
        tmp_path / "hud-round.png",
        40,
        40,
        [(10, 7, 22, 34)],
        (255, 143, 0),
    )

    first = calibrate_hud_digits(
        [("round", "1")],
        input_prefix=prefix,
        output_path=output,
        replace=True,
    )
    second = calibrate_hud_digits(
        [("round", "1")],
        input_prefix=prefix,
        output_path=output,
    )

    assert len(first.templates) == 1
    assert second == first
