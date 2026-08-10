import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroWindow,
    ExternalBalatroObservation,
    PhaseDetection,
    WindowRect,
)
from games.balatro.live.external.hud_digit_templates import load_hud_digit_templates
from games.balatro.live.external.hud_live_calibration import calibrate_live_hud_digits


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


def _fake_signatures(image, field, *, expected_digits, columns, rows):
    return tuple(
        tuple([index + 1] * (columns * rows))
        for index in range(expected_digits)
    )


def test_live_hud_calibration_appends_to_existing_templates(tmp_path, monkeypatch):
    output = tmp_path / "digits.json"
    monkeypatch.setattr(
        "games.balatro.live.external.hud_live_calibration.extract_hud_digit_signatures",
        _fake_signatures,
    )

    calibrate_live_hud_digits(
        _observation(),
        [("hands", "2")],
        output_path=output,
        replace=True,
    )
    templates = calibrate_live_hud_digits(
        _observation(),
        [("blind_target", "59")],
        output_path=output,
    )

    assert templates.coverage == {"2", "5", "9"}
    assert load_hud_digit_templates(output).coverage == {"2", "5", "9"}


def test_live_hud_calibration_rejects_unknown_field(tmp_path):
    with pytest.raises(ValueError, match="unknown HUD field"):
        calibrate_live_hud_digits(
            _observation(),
            [("unknown", "2")],
            output_path=tmp_path / "digits.json",
            replace=True,
        )


def test_live_hud_calibration_rejects_non_hand_phase(tmp_path):
    with pytest.raises(ValueError, match="requires SELECTING_HAND"):
        calibrate_live_hud_digits(
            _observation("SHOP"),
            [("hands", "2")],
            output_path=tmp_path / "digits.json",
            replace=True,
        )
