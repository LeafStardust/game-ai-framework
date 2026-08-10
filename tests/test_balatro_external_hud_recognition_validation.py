import sys
from types import SimpleNamespace

import pytest

from games.balatro.live.external import hud_recognition_validation as validation


class _FakeObserver:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def observe(self):
        self.events.append("observe")
        return SimpleNamespace(
            phase=SimpleNamespace(phase="SELECTING_HAND"),
            frame=object(),
        )


def test_hud_validation_waits_before_live_capture(monkeypatch):
    events = []
    monkeypatch.setattr(validation, "DEFAULT_HUD_FIELD_REGIONS", {})
    monkeypatch.setattr(validation, "load_hud_digit_templates", lambda path: object())
    monkeypatch.setattr(validation, "BalatroViewport", lambda frame: object())
    monkeypatch.setattr(validation.time, "sleep", lambda seconds: events.append(("sleep", seconds)))
    monkeypatch.setattr(
        validation.ExternalBalatroObserver,
        "from_template_file",
        lambda path: _FakeObserver(events),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["hud_recognition_validation", "--prepare-delay", "1.5"],
    )

    assert validation.main() == 0
    assert events == [("sleep", 1.5), "observe"]


def test_hud_validation_rejects_negative_prepare_delay(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["hud_recognition_validation", "--prepare-delay", "-1"],
    )

    with pytest.raises(SystemExit) as error:
        validation.main()

    assert error.value.code == 2
