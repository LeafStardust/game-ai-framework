import json

import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroWindow,
    ExternalBalatroObservation,
    PhaseDetection,
    WindowRect,
)
from games.balatro.live.external.hud_capture import (
    DEFAULT_HUD_FIELD_REGIONS,
    DEFAULT_HUD_REGION,
    save_hud_diagnostic,
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


def test_default_hud_field_regions_fit_inside_hud_panel():
    assert set(DEFAULT_HUD_FIELD_REGIONS) == {
        "ante",
        "blind_target",
        "discards",
        "hands",
        "money",
        "round",
        "score",
    }
    for region in DEFAULT_HUD_FIELD_REGIONS.values():
        assert region.left >= DEFAULT_HUD_REGION.left
        assert region.top >= DEFAULT_HUD_REGION.top
        assert region.right <= DEFAULT_HUD_REGION.right
        assert region.bottom <= DEFAULT_HUD_REGION.bottom


def test_refined_hud_regions_are_value_focused():
    assert DEFAULT_HUD_REGION.width == 0.27
    assert DEFAULT_HUD_FIELD_REGIONS["blind_target"].top == 0.21
    assert DEFAULT_HUD_FIELD_REGIONS["score"].top == 0.37
    assert DEFAULT_HUD_FIELD_REGIONS["hands"].top == 0.66
    assert DEFAULT_HUD_FIELD_REGIONS["discards"].top == 0.66
    assert DEFAULT_HUD_FIELD_REGIONS["money"].top == 0.77
    assert DEFAULT_HUD_FIELD_REGIONS["ante"].top == 0.89
    assert DEFAULT_HUD_FIELD_REGIONS["round"].top == 0.89


def test_hud_diagnostic_saves_panel_fields_and_metadata(tmp_path):
    prefix = tmp_path / "hud"

    metadata = save_hud_diagnostic(_observation(), prefix)

    assert (tmp_path / "hud-full.png").exists()
    assert (tmp_path / "hud-panel.png").exists()
    for name in DEFAULT_HUD_FIELD_REGIONS:
        assert (tmp_path / f"hud-{name}.png").exists()

    saved = json.loads((tmp_path / "hud.json").read_text(encoding="utf-8"))
    assert saved == metadata
    assert metadata["phase"] == "SELECTING_HAND"
    assert metadata["hud_region"]["normalized"] == {
        "left": DEFAULT_HUD_REGION.left,
        "top": DEFAULT_HUD_REGION.top,
        "width": DEFAULT_HUD_REGION.width,
        "height": DEFAULT_HUD_REGION.height,
    }
    assert metadata["hud_region"]["pixels"]["width"] == 27
    assert metadata["hud_region"]["pixels"]["height"] == 80
    assert sorted(metadata["fields"]) == sorted(DEFAULT_HUD_FIELD_REGIONS)


def test_hud_diagnostic_supports_custom_field_regions(tmp_path):
    fields = {
        "money": DEFAULT_HUD_FIELD_REGIONS["money"],
    }

    metadata = save_hud_diagnostic(
        _observation(),
        tmp_path / "hud",
        field_regions=fields,
    )

    assert list(metadata["fields"]) == ["money"]
    assert (tmp_path / "hud-money.png").exists()
    assert not (tmp_path / "hud-score.png").exists()


def test_hud_diagnostic_rejects_non_hand_phase(tmp_path):
    with pytest.raises(ValueError, match="requires SELECTING_HAND"):
        save_hud_diagnostic(
            _observation("SHOP"),
            tmp_path / "hud",
        )

    assert not (tmp_path / "hud-full.png").exists()
    assert not (tmp_path / "hud-panel.png").exists()
    assert not (tmp_path / "hud.json").exists()
