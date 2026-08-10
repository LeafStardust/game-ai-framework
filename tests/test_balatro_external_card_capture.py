import json

import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroWindow,
    ExternalBalatroObservation,
    PhaseDetection,
    WindowRect,
)
from games.balatro.live.external.card_capture import (
    DEFAULT_HAND_REGION,
    save_card_diagnostic,
)


def _observation(phase="SELECTING_HAND", width=100, height=80):
    frame = BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=1,
            title="Balatro",
            client_rect=WindowRect(10, 20, width, height),
        ),
        width=width,
        height=height,
        bgra=b"\x0a\x14\x1e\xff" * (width * height),
    )
    return ExternalBalatroObservation(
        frame=frame,
        phase=PhaseDetection(phase, 0.99, 0.01),
    )


def test_card_diagnostic_saves_full_frame_hand_crop_and_metadata(tmp_path):
    prefix = tmp_path / "cards"

    metadata = save_card_diagnostic(_observation(), prefix)

    assert (tmp_path / "cards-full.png").exists()
    assert (tmp_path / "cards-hand.png").exists()
    saved = json.loads((tmp_path / "cards.json").read_text(encoding="utf-8"))
    assert saved == metadata
    assert metadata["phase"] == "SELECTING_HAND"
    assert metadata["hand_region"]["normalized"] == {
        "left": DEFAULT_HAND_REGION.left,
        "top": DEFAULT_HAND_REGION.top,
        "width": DEFAULT_HAND_REGION.width,
        "height": DEFAULT_HAND_REGION.height,
    }
    assert metadata["hand_region"]["pixels"]["width"] == 84
    assert metadata["hand_region"]["pixels"]["height"] == 40


def test_card_diagnostic_rejects_non_hand_phase(tmp_path):
    with pytest.raises(ValueError, match="requires SELECTING_HAND"):
        save_card_diagnostic(
            _observation("SHOP"),
            tmp_path / "cards",
        )

    assert not (tmp_path / "cards-full.png").exists()
    assert not (tmp_path / "cards-hand.png").exists()
    assert not (tmp_path / "cards.json").exists()
