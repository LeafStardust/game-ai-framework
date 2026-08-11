import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroMouseController,
    BalatroViewport,
    BalatroWindow,
    MouseControlNotArmed,
    NormalizedPoint,
    NormalizedRect,
    PixelPoint,
    WindowRect,
)
from games.balatro.live.external.mouse import WindowsMouseInputProvider


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


class FocusRecoveryUser32:

    def __init__(self):
        self.foreground = 100
        self.attached_threads = set()
        self.events = []

    @staticmethod
    def _handle_value(hwnd):
        return int(getattr(hwnd, "value", hwnd) or 0)

    def SetProcessDPIAware(self):
        return 1

    def GetForegroundWindow(self):
        return self.foreground

    def IsWindow(self, hwnd):
        return int(self._handle_value(hwnd) in {42, 100})

    def IsIconic(self, hwnd):
        return 0

    def BringWindowToTop(self, hwnd):
        self.events.append(("top", self._handle_value(hwnd)))
        return 1

    def SetForegroundWindow(self, hwnd):
        handle = self._handle_value(hwnd)
        self.events.append(("foreground", handle))
        if self.attached_threads:
            self.foreground = handle
        return 1

    def GetWindowThreadProcessId(self, hwnd, _process_id):
        return {100: 10, 42: 20}.get(self._handle_value(hwnd), 0)

    def AttachThreadInput(self, current_thread, other_thread, attach):
        event = ("attach", int(current_thread), int(other_thread), bool(attach))
        self.events.append(event)
        if attach:
            self.attached_threads.add(int(other_thread))
        else:
            self.attached_threads.discard(int(other_thread))
        return 1


class FocusRecoveryKernel32:

    def GetCurrentThreadId(self):
        return 30


def _viewport():
    frame = BalatroFrame(
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
    return BalatroViewport(frame)


def test_mouse_controller_is_disarmed_by_default():
    controller = BalatroMouseController(provider=Provider())

    with pytest.raises(MouseControlNotArmed):
        controller.click_screen(PixelPoint(10, 20))


def test_mouse_controller_clicks_screen_coordinate_when_armed():
    provider = Provider()
    controller = BalatroMouseController(provider=provider, armed=True, hover_delay=0)

    controller.click_screen(
        PixelPoint(300, 400),
        window=_viewport().frame.window,
    )

    assert provider.events == [
        ("focus", 42),
        ("move", 300, 400),
        ("down",),
        ("up",),
    ]


def test_mouse_controller_waits_after_move_before_click(monkeypatch):
    provider = Provider()
    sleeps = []
    controller = BalatroMouseController(
        provider=provider,
        armed=True,
        hover_delay=0.1,
    )
    monkeypatch.setattr(
        "games.balatro.live.external.mouse.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    controller.click_screen(PixelPoint(300, 400))

    assert provider.events == [
        ("move", 300, 400),
        ("down",),
        ("up",),
    ]
    assert sleeps == [0.1]


def test_mouse_controller_maps_normalized_point_to_real_screen():
    provider = Provider()
    controller = BalatroMouseController(provider=provider, armed=True, hover_delay=0)

    controller.click(_viewport(), NormalizedPoint(0.5, 0.25))

    assert provider.events == [
        ("focus", 42),
        ("move", 300, 250),
        ("down",),
        ("up",),
    ]


def test_mouse_controller_clicks_normalized_rectangle_center():
    provider = Provider()
    controller = BalatroMouseController(provider=provider, armed=True, hover_delay=0)

    controller.click_rect(
        _viewport(),
        NormalizedRect(0.25, 0.25, 0.5, 0.5),
    )

    assert provider.events[1] == ("move", 300, 300)


def test_mouse_controller_can_be_disarmed_after_use():
    controller = BalatroMouseController(provider=Provider(), armed=True)
    controller.disarm()

    with pytest.raises(MouseControlNotArmed):
        controller.move_screen(PixelPoint(1, 1))


def test_windows_provider_recovers_focus_with_attached_input_threads():
    user32 = FocusRecoveryUser32()
    provider = WindowsMouseInputProvider(
        user32=user32,
        kernel32=FocusRecoveryKernel32(),
        focus_retry_delay=0,
    )

    provider.focus(42)

    assert user32.foreground == 42
    assert user32.attached_threads == set()
    assert ("attach", 30, 10, True) in user32.events
    assert ("attach", 30, 20, True) in user32.events
    assert ("attach", 30, 20, False) in user32.events
    assert ("attach", 30, 10, False) in user32.events
