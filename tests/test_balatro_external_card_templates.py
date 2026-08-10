import json

import pytest

from games.balatro.live.external.capture import save_bgra_png
from games.balatro.live.external.card_aligned_features import (
    aligned_rank_shape_signature,
    aligned_suit_color_signature,
)
from games.balatro.live.external.card_calibration import (
    calibrate_card_template_manifests,
    calibrate_card_templates,
)
from games.balatro.live.external.card_templates import (
    coverage_report,
    load_card_template_set,
    load_rgb_png,
    parse_card_label,
    templates_from_labeled_images,
)


def _identity_png(
    path,
    *,
    accent=(20, 30, 40),
    rank_offset=(0, 0),
    rank_width=4,
):
    width = 24
    height = 32
    pixels = bytearray(b"\xf0\xf0\xf0\xff" * (width * height))
    blue, green, red = accent
    offset_x, offset_y = rank_offset

    for y in range(3 + offset_y, 8 + offset_y):
        for x in range(2 + offset_x, 2 + offset_x + rank_width):
            index = (y * width + x) * 4
            pixels[index : index + 4] = bytes((blue, green, red, 255))

    suit_top = 10
    for y in range(suit_top, suit_top + 5):
        for x in range(3, 8):
            if abs(x - 5) + abs(y - (suit_top + 2)) <= 3:
                index = (y * width + x) * 4
                pixels[index : index + 4] = bytes((blue, green, red, 255))

    save_bgra_png(width, height, bytes(pixels), path)
    return path


def _manifest(directory, labels, *, accent=(20, 30, 40)):
    directory.mkdir()
    cards = []
    for index, label in enumerate(labels):
        name = f"card-{index:02d}.png"
        _identity_png(directory / name, accent=accent)
        cards.append({"index": index, "file": name, "label": label})

    path = directory / "labels.json"
    path.write_text(json.dumps({"cards": cards}), encoding="utf-8")
    return path


def _aligned_rank(image, *, columns=8, rows=8):
    return aligned_rank_shape_signature(
        image,
        aligned_suit_color_signature(image),
        columns=columns,
        rows=rows,
    )


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


def test_aligned_rank_shape_signature_is_color_invariant(tmp_path):
    dark = load_rgb_png(
        _identity_png(tmp_path / "dark.png", accent=(20, 30, 40))
    )
    colored = load_rgb_png(
        _identity_png(tmp_path / "colored.png", accent=(60, 50, 180))
    )

    dark_signature = _aligned_rank(dark)
    colored_signature = _aligned_rank(colored)

    assert len(dark_signature) == 64
    assert dark_signature == colored_signature
    assert max(dark_signature) > 0


def test_aligned_rank_shape_signature_normalizes_glyph_position(tmp_path):
    first = load_rgb_png(_identity_png(tmp_path / "first.png"))
    shifted = load_rgb_png(
        _identity_png(tmp_path / "shifted.png", rank_offset=(1, 1))
    )

    assert _aligned_rank(first, columns=20, rows=20) == _aligned_rank(
        shifted,
        columns=20,
        rows=20,
    )


def test_aligned_rank_shape_signature_preserves_glyph_aspect_ratio(tmp_path):
    square = load_rgb_png(_identity_png(tmp_path / "square.png"))
    wide = load_rgb_png(_identity_png(tmp_path / "wide.png", rank_width=6))

    assert _aligned_rank(square, columns=20, rows=20) != _aligned_rank(
        wide,
        columns=20,
        rows=20,
    )


def test_aligned_suit_color_signature_preserves_glyph_color(tmp_path):
    first = load_rgb_png(
        _identity_png(tmp_path / "first.png", accent=(20, 30, 40))
    )
    second = load_rgb_png(
        _identity_png(tmp_path / "second.png", accent=(40, 80, 180))
    )

    first_signature = aligned_suit_color_signature(first)
    second_signature = aligned_suit_color_signature(second)

    assert first_signature == (40, 30, 20)
    assert second_signature == (180, 80, 40)
    assert first_signature != second_signature


def test_templates_report_partial_rank_and_suit_coverage(tmp_path):
    first = _identity_png(tmp_path / "first.png")
    second = _identity_png(tmp_path / "second.png", accent=(40, 20, 10))
    templates = templates_from_labeled_images(
        [first, second],
        ["K♥", "7♦"],
        columns=8,
        rows=8,
    )

    report = coverage_report(templates)

    assert report["ranks"] == ["K", "7"]
    assert report["suits"] == ["Hearts", "Diamonds"]
    assert len(templates.ranks[0].signature) == 64
    assert len(templates.suits[0].signature) == 3
    assert "A" in report["missing_ranks"]
    assert "Clubs" in report["missing_suits"]
    assert report["complete"] is False


def test_calibration_uses_relative_manifest_image_paths(tmp_path):
    manifest = _manifest(
        tmp_path / "identities",
        ["Q♠", "2♣"],
        accent=(10, 20, 60),
    )
    output = tmp_path / "templates.json"

    report = calibrate_card_templates(manifest, output, append=False)
    templates = load_card_template_set(output)

    assert report["ranks"] == ["Q", "2"]
    assert report["suits"] == ["Spades", "Clubs"]
    assert len(templates.ranks) == 2
    assert len(templates.suits) == 2


def test_calibration_rebuilds_from_multiple_manifests(tmp_path):
    first = _manifest(tmp_path / "first", ["AH", "KD"])
    second = _manifest(
        tmp_path / "second",
        ["QS", "JC"],
        accent=(50, 70, 120),
    )
    output = tmp_path / "templates.json"

    report = calibrate_card_template_manifests(
        [first, second],
        output,
        replace=True,
    )
    templates = load_card_template_set(output)

    assert report["ranks"] == ["A", "K", "Q", "J"]
    assert report["suits"] == ["Hearts", "Diamonds", "Spades", "Clubs"]
    assert len(templates.ranks) == 4
    assert len(templates.suits) == 4


@pytest.mark.parametrize("version", [1, 2, 3])
def test_load_card_template_set_rejects_legacy_versions(tmp_path, version):
    path = tmp_path / "legacy.json"
    path.write_text(
        json.dumps(
            {
                "version": version,
                "columns": 12,
                "rows": 12,
                "ranks": [],
                "suits": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=f"legacy card template version {version}",
    ):
        load_card_template_set(path)
