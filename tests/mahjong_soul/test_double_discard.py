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
        batches.append([values[i].data.mouse.dwFlags for i in range(count)] if not hasattr(values,"_obj") else [values._obj.data.mouse.dwFlags])
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


def test_module_cli_uses_canonical_plan_type_before_controller_submit(tmp_path):
    import json
    import subprocess
    import sys
    report, profile = inputs()
    capture = tmp_path / "capture.jsonl"; capture.write_text("", encoding="utf-8")
    layout = tmp_path / "layout.json"; layout.write_text(json.dumps(profile), encoding="utf-8")
    script = r"""
import runpy,sys
from tests.mahjong_soul.test_input import inputs
from games.mahjong_soul.live.runtime.input import board_token
import games.mahjong_soul.live.runtime.reader as reader
import games.mahjong_soul.live.runtime.monitor as monitor
import games.mahjong_soul.live.runtime.windows_input as windows
import games.mahjong_soul.live.runtime.controller as controller
import games.mahjong_soul.live.external.schema as schema
report,profile=inputs()
class Reader:
 def __init__(self,*args):pass
 def snapshot(self):return report
class Tail:
 bad_rows=0;pending=False;reset=False
 def __init__(self,*args):pass
 def read(self):return []
class Mouse:
 def client_geometry(self):return {"width":1280,"height":720}
 def click(self,*args):raise AssertionError("No real input in regression")
 def double_click(self,*args):raise AssertionError("No real input in regression")
reader.GameReader=Reader;monitor.CaptureTail=Tail;windows.WindowsMouse=Mouse
schema.LiqiSchema.load=lambda *args:None
original=controller.InputController.submit
def check(self,plan,report,**kwargs):
 assert type(plan) in self._executors,"Wrong __main__ plan type"
 assert plan.double_click
 print("CANONICAL_PLAN_OK",flush=True)
 raise ValueError("Test stops before input")
controller.InputController.submit=check
sys.argv=["input", "--capture",sys.argv[1],"--profile",sys.argv[2],"--slot","0",
 "--tile","0p","--double-click","--execute","--expected-token",board_token(report)]
runpy.run_module("games.mahjong_soul.live.runtime.input",run_name="__main__")
"""
    result = subprocess.run([sys.executable, "-c", script, str(capture), str(layout)],
                            capture_output=True, text=True, timeout=15)
    assert "CANONICAL_PLAN_OK" in result.stdout, result.stderr
    assert result.returncode == 2 and "Test stops before input" in result.stderr



def test_cursor_parking_sends_no_button_press(monkeypatch):
    mouse,batches,delays=backend(monkeypatch)
    mouse.park(1920,1080)
    assert batches==[[0xC001]] and not delays
