import json

import pytest

from games.balatro.live.external.capture import save_bgra_png
from games.balatro.live.external.card_calibration import calibrate_card_templates
from games.balatro.live.external.card_templates import (
    RANK_ZONE,
    SUIT_ZONE,
    coverage_report,
    image_signature,
    load_card_template_set,
    load_rgb_png,
    parse_card_label,
    templates_from_labeled_images,
)


def _identity_png(path, *, accent=(20, 30, 40)):
    width = 24
    height = 32
    pixels = bytearray(b"\xf0\xf0\xf0\xff" * (width * height))
    blue, green, red = accent
    for y in range(3, 27):
        for x in range(2, 9):
            index = (y * width + x) * 4
            pixels[index : index + 4] = bytes((blue, green, red, 255))
    save_bgra_png(width, height, bytes(pixels), path)
    return path


def test_parse_card_label_accepts_symbols_and_ascii_suits():
    assert parse_card_label("K♥") == ("K", "Hearts")
    assert parse_card_label("10D") == ("10", "Diamonds")
    assert parse_card_label("qs") == ("Q", "Spades")
    assert parse_card_label("7c") == ("7", "Clubs")


def test_parse_card_label_rejects_unknown_rank_or_suit():
    with pytest.raises(ValueError, match="rank"):
        parse_card_label("1H")

    with pytest.raises(ValueError, match="suit"):
        parse_card_label("KX")


def test_load_rgb_png_reads_capture_png(tmp_path):
    path = _identity_png(tmp_path / "card.png")

    image = load_rgb_png(path)

    assert (image.width, image.height) == (24, 32)
    assert len(image.rgb) == 24 * 32 * 3


def test_image_signature_has_stable_grid_size(tmp_path):
    image = load_rgb_png(_identity_png(tmp_path / "card.png"))

    rank = image_signature(image, RANK_ZONE, columns=4, rows=3)
    suit = image_signature(image, SUIT_ZONE, columns=4, rows=3)

    assert len(rank) == 12
    assert len(suit) == 12
    assert max(rank) > 0
    assert max(suit) > 0


def test_templates_report_partial_rank_and_suit_coverage(tmp_path):
    first = _identity_png(tmp_path / "first.png")
    second = _identity_png(tmp_path / "second.png", accent=(40, 20, 10))
    templates = templates_from_labeled_images(
        [first, second],
        ["K♥", "7♦"],
        columns=4,
        rows=4,
    )

    report = coverage_report(templates)

    assert report["ranks"] == ["K", "7"]
    assert report["suits"] == ["Hearts", "Diamonds"]
    assert "A" in report["missing_ranks"]
    assert "Clubs" in report["missing_suits"]
    assert report["complete"] is False


def test_calibration_uses_relative_manifest_image_paths(tmp_path):
    identity_dir = tmp_path / "identities"
    identity_dir.mkdir()
    _identity_png(identity_dir / "card-00.png")
    _identity_png(identity_dir / "card-01.png", accent=(10, 20, 60))
    manifest = identity_dir / "labels.json"
    manifest.write_text(
        json.dumps(
            {
                "cards": [
                    {"index": 0, "file": "card-00.png", "label": "Q♠"},
                    {"index": 1, "file": "card-01.png", "label": "2♣"},
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "templates.json"

    report = calibrate_card_templates(manifest, output, append=False)
    templates = load_card_template_set(output)

    assert report["ranks"] == ["Q", "2"]
    assert report["suits"] == ["Spades", "Clubs"]
    assert len(templates.ranks) == 2
    assert len(templates.suits) == 2
