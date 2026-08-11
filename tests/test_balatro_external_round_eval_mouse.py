from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.mouse import BalatroMouseController
from games.balatro.live.external.round_eval_mouse import (
    ExternalRoundEvalMouseExecutor,
    RoundEvalMouseLayout,
    RoundEvalMouseLayoutError,
)
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


class Capture:

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


def test_round_eval_layout_round_trips(tmp_path):
    path = tmp_path / "round-eval.json"
    layout = RoundEvalMouseLayout(cash_out=NormalizedPoint(0.75, 0.8))

    layout.save(path)
    loaded = RoundEvalMouseLayout.load(path)

    assert loaded == layout
    assert loaded.point_for("cash-out") == NormalizedPoint(0.75, 0.8)
    assert loaded.point_for("cash_out") == NormalizedPoint(0.75, 0.8)


def test_round_eval_layout_requires_cash_out_calibration():
    try:
        RoundEvalMouseLayout().point_for("cash-out")
    except RoundEvalMouseLayoutError as error:
        assert "not calibrated" in str(error)
    else:
        raise AssertionError("uncalibrated cash-out should fail")


def test_round_eval_executor_focuses_then_clicks_cash_out():
    provider = Provider()
    layout = RoundEvalMouseLayout(cash_out=NormalizedPoint(0.75, 0.8))
    executor = ExternalRoundEvalMouseExecutor(
        layout,
        capture=Capture(_frame(), provider),
        mouse=BalatroMouseController(provider=provider, armed=True, hover_delay=0),
        focus_settle_delay=0,
    )

    executor.dispatch()

    assert provider.events == [
        ("focus", 42),
        ("move", 399, 359),
        ("down",),
        ("up",),
    ]
