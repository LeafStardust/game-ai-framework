from dataclasses import replace
from copy import deepcopy
import pytest

from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import plan_discard
from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
from tests.mahjong_soul.test_input import inputs, Mouse
from tests.mahjong_soul.test_controller import confirmed


class DoubleMouse(Mouse):
    def double_click(self, *args):
        self.clicks.extend([args, args])


def test_double_discard_is_one_controller_action_with_matching_server_ack():
    report, profile = inputs(); mouse = DoubleMouse(); controller = InputController(mouse)
    plan = replace(plan_discard(report, profile, 0, "0p", now=10), double_click=True)
    controller.submit(plan, report, enabled=True, now=10)
    assert len(mouse.clicks) == 2
    assert not controller.observe("other", confirmed(), now=11)
    with pytest.raises(ValueError): controller.confirm_selection(plan, report, "0p", enabled=True, now=11)
    with pytest.raises(ValueError): controller.submit(plan, report, enabled=True, now=11)
    assert len(mouse.clicks) == 2
    assert controller.observe("game", confirmed(), now=11)
    with pytest.raises(ValueError): controller.submit(plan, report, enabled=True, now=11)
    assert len(mouse.clicks) == 2


@pytest.mark.parametrize("failure", ["stale", "expired", "disabled", "partial", "no_ack"])
def test_double_discard_guards_and_failures_never_retry(failure):
    report, profile = inputs(); mouse = DoubleMouse(); controller = InputController(mouse)
    plan = replace(plan_discard(report, profile, 0, "0p", now=10), double_click=True)
    if failure == "stale": report["state"]["step"] += 1
    if failure == "partial":
        def partial(*args):
            mouse.clicks.append(args)
            raise OSError("Partial double-click")
        mouse.double_click = partial
    if failure != "no_ack":
        with pytest.raises((ValueError, OSError)):
            controller.submit(plan, report, enabled=failure != "disabled", now=12 if failure == "expired" else 10)
        assert len(mouse.clicks) == (1 if failure == "partial" else 0)
    else:
        controller.submit(plan, report, enabled=True, now=10)
        assert controller.update(report, now=15)["status"] == "blocked"
    if failure in {"partial", "no_ack"}:
        count = len(mouse.clicks)
        with pytest.raises(ValueError): controller.submit(plan, report, enabled=True, now=11)
        assert len(mouse.clicks) == count


class Function:
    def __init__(self, call): self.call = call
    def __call__(self, *args): return self.call(*args)


def backend(monkeypatch, *, change=None, partial=False):
    mouse = WindowsMouse.__new__(WindowsMouse)
    mouse._foreground = lambda: 1
    geometry = {"width": 1920, "height": 1080, "left": 0, "top": 0}
    moved = [False]; batches = []; delays = []
    class User: pass
    mouse.user = User()
    mouse.user.SetThreadDpiAwarenessContext = Function(lambda value: 1)
    mouse.user.GetSystemMetrics = Function(lambda key: {76:0,77:0,78:1920,79:1080}[key])
    def send(count, values, size):
        batches.append([values[i].data.mouse.dwFlags for i in range(count)] if count > 1 else [4])
        return 2 if partial and count == 3 else count
    mouse.user.SendInput = Function(send)
    mouse._client_geometry = lambda hwnd: {**geometry, "left": 5} if moved[0] and change == "move" else dict(geometry)
    def pause(seconds):
        delays.append(seconds); moved[0] = True
        if change == "focus": mouse._foreground = lambda: 2
    monkeypatch.setattr("games.mahjong_soul.live.runtime.windows_input.time.sleep", pause)
    return mouse, batches, delays


def test_native_double_click_sends_two_presses_with_short_interval(monkeypatch):
    mouse, batches, delays = backend(monkeypatch)
    mouse.double_click(.2, .9, 1920, 1080)
    assert batches == [[0xC001, 2, 4], [0xC001, 2, 4]]
    assert delays == [.08]


@pytest.mark.parametrize("change", ["move", "focus"])
def test_native_double_click_stops_if_window_changes_between_clicks(monkeypatch, change):
    mouse, batches, _ = backend(monkeypatch, change=change)
    with pytest.raises(ValueError): mouse.double_click(.2, .9, 1920, 1080)
    assert len(batches) == 1


def test_native_partial_double_click_releases_and_stops(monkeypatch):
    mouse, batches, delays = backend(monkeypatch, partial=True)
    with pytest.raises(OSError): mouse.double_click(.2, .9, 1920, 1080)
    assert batches == [[0xC001, 2, 4], [4]]
    assert delays == []
