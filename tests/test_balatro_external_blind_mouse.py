from games.balatro.live.external.blind_mouse import (
    BlindMouseLayout,
    BlindMouseLayoutError,
    ExternalBlindMouseExecutor,
)
from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.mouse import BalatroMouseController
from games.balatro.live.external.viewport import NormalizedPoint
from games.balatro.live.external.window import BalatroWindow, WindowRect


class Provider:

    def __init__(self):
        self.events = []

    def focus(self, handle):
        self.events.append(("focus", handle))

    def move_to(self, x, y):
        self.events.append(("move", x, y))

    def left_down(self):
        self.events.append(("down",))

    def left_up(self):
        self.events.append(("up",))


class Tracker:

    def __init__(self, window):
        self.window = window

    def snapshot(self):
        return self.window


class ForegroundCapture:

    def __init__(self, frame, provider):
        self.frame = frame
        self.provider = provider
        self.tracker = Tracker(frame.window)

    def capture(self):
        assert self.provider.events[0] == ("focus", 42)
        return self.frame

    def close(self):
        pass


def _frame():
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=42,
            title="Balatro",
            client_rect=WindowRect(100, 200, 400, 200),
        ),
        width=400,
        height=200,
        bgra=bytes(400 * 200 * 4),
    )


def test_blind_mouse_layout_round_trips_select_and_skip(tmp_path):
    path = tmp_path / "blind.json"
    layout = BlindMouseLayout(
        small_select=NormalizedPoint(0.2, 0.6),
        small_skip=NormalizedPoint(0.2, 0.8),
        big_select=NormalizedPoint(0.5, 0.6),
        big_skip=NormalizedPoint(0.5, 0.8),
        boss_select=NormalizedPoint(0.8, 0.6),
    )

    layout.save(path)
    loaded = BlindMouseLayout.load(path)

    assert loaded == layout
    assert loaded.point_for("big-select") == NormalizedPoint(0.5, 0.6)
    assert loaded.point_for("big-skip") == NormalizedPoint(0.5, 0.8)


def test_blind_mouse_layout_reads_legacy_select_only_format():
    layout = BlindMouseLayout.from_dict(
        {
            "small": {"x": 0.2, "y": 0.6},
            "big": {"x": 0.5, "y": 0.6},
            "boss": {"x": 0.8, "y": 0.6},
        }
    )

    assert layout.point_for("small-select") == NormalizedPoint(0.2, 0.6)
    assert layout.point_for("boss-select") == NormalizedPoint(0.8, 0.6)


def test_blind_mouse_layout_rejects_uncalibrated_control():
    layout = BlindMouseLayout(big_select=NormalizedPoint(0.5, 0.6))

    try:
        layout.point_for("big-skip")
    except BlindMouseLayoutError as error:
        assert "not calibrated" in str(error)
    else:
        raise AssertionError("uncalibrated big-skip control should fail")


def test_blind_mouse_layout_rejects_boss_skip():
    layout = BlindMouseLayout(boss_select=NormalizedPoint(0.8, 0.6))

    try:
        layout.point_for("boss-skip")
    except BlindMouseLayoutError as error:
        assert "unsupported blind control" in str(error)
    else:
        raise AssertionError("boss-skip should not be a supported control")


def test_blind_mouse_executor_focuses_then_clicks_control():
    provider = Provider()
    frame = _frame()
    executor = ExternalBlindMouseExecutor(
        BlindMouseLayout(big_skip=NormalizedPoint(0.5, 0.5)),
        capture=ForegroundCapture(frame, provider),
        mouse=BalatroMouseController(
            provider=provider,
            armed=True,
            hover_delay=0,
        ),
        focus_settle_delay=0,
    )

    executor.dispatch("big-skip")

    assert provider.events == [
        ("focus", 42),
        ("move", 300, 300),
        ("down",),
        ("up",),
    ]
