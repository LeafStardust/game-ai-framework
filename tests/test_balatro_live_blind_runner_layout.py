from games.balatro.live.external import live_blind_runner


class _Layout:
    def __init__(self):
        self.points = []

    def point_for(self, name):
        self.points.append(name)
        return object()


def test_dry_run_does_not_load_mouse_layout(monkeypatch):
    def fail_load(path):
        raise AssertionError("dry run must not load mouse calibration")

    monkeypatch.setattr(live_blind_runner.HandMouseLayout, "load", fail_load)

    assert live_blind_runner._load_execution_layout(False, "missing.json") is None


def test_execute_loads_and_validates_mouse_layout(monkeypatch):
    layout = _Layout()

    monkeypatch.setattr(
        live_blind_runner.HandMouseLayout,
        "load",
        lambda path: layout,
    )

    result = live_blind_runner._load_execution_layout(True, "layout.json")

    assert result is layout
    assert layout.points == ["play-hand", "discard"]
