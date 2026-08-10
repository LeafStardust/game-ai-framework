import pytest

from games.balatro.live.external.card_recognition import (
    _match_signature,
    _rgb_image_from_region,
)
from games.balatro.live.external.card_templates import CardVisualTemplate
from games.balatro.live.external.viewport import FrameRegion, NormalizedRect, PixelRect


def test_match_signature_groups_duplicate_labels_by_best_template():
    templates = (
        CardVisualTemplate("K", (0, 0, 0, 0)),
        CardVisualTemplate("K", (100, 100, 100, 100)),
        CardVisualTemplate("Q", (200, 200, 200, 200)),
    )

    match = _match_signature((90, 90, 90, 90), templates)

    assert match.label == "K"
    assert match.runner_up == "Q"
    assert match.distance == pytest.approx(10 / 255)
    assert match.margin == pytest.approx(100 / 255)


def test_match_signature_reports_exact_match_with_positive_margin():
    templates = (
        CardVisualTemplate("Hearts", (10, 20, 30)),
        CardVisualTemplate("Spades", (30, 40, 50)),
    )

    match = _match_signature((10, 20, 30), templates)

    assert match.label == "Hearts"
    assert match.distance == 0.0
    assert match.confidence == 1.0
    assert match.margin > 0.0


def test_match_signature_rejects_empty_or_mismatched_templates():
    with pytest.raises(ValueError, match="at least one template"):
        _match_signature((1, 2), ())

    with pytest.raises(ValueError, match="dimensions"):
        _match_signature((1, 2), (CardVisualTemplate("K", (1,)),))


def test_rgb_image_from_region_converts_bgra_to_rgb():
    region = FrameRegion(
        normalized_rect=NormalizedRect(0.0, 0.0, 1.0, 1.0),
        pixel_rect=PixelRect(0, 0, 2, 1),
        width=2,
        height=1,
        bgra=bytes((10, 20, 30, 255, 40, 50, 60, 255)),
    )

    image = _rgb_image_from_region(region)

    assert image.width == 2
    assert image.height == 1
    assert image.rgb == bytes((30, 20, 10, 60, 50, 40))
