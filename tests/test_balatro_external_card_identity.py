import json

import pytest

from games.balatro.live.external.card_identity import (
    card_identity_rect,
    extract_card_identity_regions,
    save_card_identity_labels,
)
from games.balatro.live.external.card_locator import CardFaceLocation
from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.viewport import (
    BalatroViewport,
    NormalizedRect,
    PixelRect,
)
from games.balatro.live.external.window import BalatroWindow, WindowRect


def _frame(width=1000, height=500):
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=1,
            title="Balatro",
            client_rect=WindowRect(0, 0, width, height),
        ),
        width=width,
        height=height,
        bgra=b"\x20\x20\x20\xff" * (width * height),
    )


def _card(left=0.2, top=0.5, width=0.1, height=0.3):
    return CardFaceLocation(
        local_rect=PixelRect(0, 0, 100, 150),
        normalized_rect=NormalizedRect(left, top, width, height),
        density=0.8,
    )


def test_card_identity_rect_uses_upper_left_card_corner():
    rect = card_identity_rect(_card(), width_ratio=0.4, height_ratio=0.5)

    assert rect.left == pytest.approx(0.2)
    assert rect.top == pytest.approx(0.5)
    assert rect.width == pytest.approx(0.04)
    assert rect.height == pytest.approx(0.15)


def test_extract_card_identity_regions_preserves_card_order():
    viewport = BalatroViewport(_frame())
    cards = [_card(left=0.2), _card(left=0.4)]

    identities = extract_card_identity_regions(
        viewport,
        cards,
        width_ratio=0.5,
        height_ratio=0.4,
    )

    assert len(identities) == 2
    assert identities[0].card is cards[0]
    assert identities[1].card is cards[1]
    assert identities[0].region.width == 50
    assert identities[0].region.height == 60
    assert identities[1].region.pixel_rect.left == 400


def test_save_card_identity_labels_writes_relative_sample_files(tmp_path):
    directory = tmp_path / "samples"
    directory.mkdir()
    metadata = {
        "cards": [
            {"file": str(directory / "card-00.png")},
            {"file": str(directory / "card-01.png")},
        ]
    }

    path = save_card_identity_labels(metadata, ["AH", "10C"], directory)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload == {
        "cards": [
            {"file": "card-00.png", "index": 0, "label": "AH"},
            {"file": "card-01.png", "index": 1, "label": "10C"},
        ]
    }


def test_save_card_identity_labels_rejects_count_mismatch(tmp_path):
    metadata = {"cards": [{"file": "card-00.png"}, {"file": "card-01.png"}]}

    with pytest.raises(ValueError, match="label count"):
        save_card_identity_labels(metadata, ["AH"], tmp_path)


def test_save_card_identity_labels_rejects_invalid_card_label(tmp_path):
    metadata = {"cards": [{"file": "card-00.png"}]}

    with pytest.raises(ValueError, match="unknown card"):
        save_card_identity_labels(metadata, ["1Z"], tmp_path)


def test_card_identity_rect_rejects_invalid_ratios():
    card = _card()

    with pytest.raises(ValueError, match="width_ratio"):
        card_identity_rect(card, width_ratio=0.0)

    with pytest.raises(ValueError, match="height_ratio"):
        card_identity_rect(card, height_ratio=1.1)
