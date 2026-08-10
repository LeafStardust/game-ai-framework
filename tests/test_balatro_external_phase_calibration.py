from games.balatro.live.external import (
    BalatroFrame,
    BalatroWindow,
    WindowRect,
)
from games.balatro.live.external.phase_calibration import (
    capture_phase_templates,
    load_phase_templates,
    save_phase_templates,
)


class Capture:

    def __init__(self, frames):
        self.frames = iter(frames)

    def capture(self):
        return next(self.frames)


def _frame(red, green, blue, width=60, height=40):
    pixel = bytes((blue, green, red, 255))
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
        bgra=pixel * width * height,
    )


def test_phase_template_file_round_trip(tmp_path):
    templates = capture_phase_templates(
        "SHOP",
        Capture([_frame(10, 20, 30)]),
        samples=1,
        delay=0,
        columns=3,
        rows=2,
    )
    path = tmp_path / "phases.json"

    save_phase_templates(path, templates)
    restored = load_phase_templates(path)

    assert restored == templates


def test_phase_calibration_captures_multiple_samples():
    templates = capture_phase_templates(
        "SELECTING_HAND",
        Capture(
            [
                _frame(10, 20, 30),
                _frame(11, 21, 31),
                _frame(12, 22, 32),
            ]
        ),
        samples=3,
        delay=0,
        columns=2,
        rows=2,
    )

    assert len(templates) == 3
    assert {template.phase for template in templates} == {"SELECTING_HAND"}


def test_phase_calibration_saves_first_capture_snapshot(tmp_path):
    snapshot = tmp_path / "shop.png"

    capture_phase_templates(
        "SHOP",
        Capture([_frame(10, 20, 30), _frame(11, 21, 31)]),
        samples=2,
        delay=0,
        columns=2,
        rows=2,
        snapshot_path=snapshot,
    )

    assert snapshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_missing_phase_template_file_loads_empty(tmp_path):
    assert load_phase_templates(tmp_path / "missing.json") == []
