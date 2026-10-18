"""Exercise the native event sequence against a fake user32, never the desktop."""
import ctypes
from types import SimpleNamespace
import pytest
from games.mahjong_soul.live.runtime.windows_input import WindowsMouse


class SendInput:
    def __init__(self,trace,fail=None):self.trace=trace;self.calls=0;self.fail=fail
    def __call__(self,count,events,size):
        self.calls+=1
        event=ctypes.cast(events,self.argtypes[1]).contents
        self.trace.append(("event",event.data.mouse.dwFlags,event.data.mouse.dx,event.data.mouse.dy))
        return 0 if self.calls==self.fail else count


def mouse(monkeypatch,fail=None):
    trace=[];m=WindowsMouse.__new__(WindowsMouse)
    m.user=SimpleNamespace(SetThreadDpiAwarenessContext=lambda value:trace.append(("dpi",)) or 1,
                           GetSystemMetrics=lambda key:{76:0,77:0,78:1920,79:1080}[key],
                           SendInput=SendInput(trace,fail))
    m._foreground=lambda:99
    m._client_geometry=lambda hwnd:{"left":0,"top":0,"width":1920,"height":1080}
    monkeypatch.setattr("games.mahjong_soul.live.runtime.windows_input.time.sleep",lambda seconds:trace.append(("wait",seconds)))
    return m,trace


def test_click_is_move_settle_press_hold_release_settle(monkeypatch):
    m,trace=mouse(monkeypatch)
    m.click(.5,.5,1920,1080)
    assert [t[:2] for t in trace if t[0]!="dpi"]==[
        ("event",0xc001),("wait",.04),("event",0xc003),
        ("wait",.08),("event",4),("wait",.08)]
    events=[t for t in trace if t[0]=="event"]
    assert events[0][2:]==events[1][2:]
    assert trace[-1]==("dpi",)


def test_double_click_has_two_distinct_holds_and_releases(monkeypatch):
    m,trace=mouse(monkeypatch);m.double_click(.5,.5,1920,1080)
    assert [t[1] for t in trace if t[0]=="event"]==[0xc001,0xc003,4]*2
    assert [t[1] for t in trace if t[0]=="wait"]==[.04,.08,.08]*2


def test_park_does_not_press_or_wait(monkeypatch):
    m,trace=mouse(monkeypatch);m.park(1920,1080)
    assert [t[1] for t in trace if t[0]=="event"]==[0xc001]
    assert not any(t[0]=="wait" for t in trace)


@pytest.mark.parametrize("fail",[1,2,3])
def test_os_delivery_failure_never_repeats_a_press_and_releases_if_uncertain(monkeypatch,fail):
    m,trace=mouse(monkeypatch,fail)
    with pytest.raises(OSError):m.double_click(.5,.5,1920,1080)
    flags=[t[1] for t in trace if t[0]=="event"]
    assert flags.count(0xc003)==(0 if fail==1 else 1)
    if fail>1:assert flags[-1]==4
    assert trace[-1]==("dpi",)


@pytest.mark.parametrize("phase",["before_press","during_hold","before_second_click"])
def test_focus_or_geometry_loss_stops_further_presses(monkeypatch,phase):
    m,trace=mouse(monkeypatch)
    changed=[False]
    m._foreground=lambda:100 if changed[0] else 99
    def wait(seconds):
        trace.append(("wait",seconds))
        waits=sum(t[0]=="wait" for t in trace)
        if waits=={"before_press":1,"during_hold":2,"before_second_click":3}[phase]:changed[0]=True
    monkeypatch.setattr("games.mahjong_soul.live.runtime.windows_input.time.sleep",wait)
    with pytest.raises(ValueError,match="Foreground changed"):m.double_click(.5,.5,1920,1080)
    flags=[t[1] for t in trace if t[0]=="event"]
    assert flags.count(0xc003)==(0 if phase=="before_press" else 1)
    if phase=="during_hold":assert flags[-1]==4
    assert trace[-1]==("dpi",)


def test_resize_during_press_releases_and_does_not_click_again(monkeypatch):
    m,trace=mouse(monkeypatch);geometry=m._client_geometry(99)
    m._client_geometry=lambda hwnd:dict(geometry)
    def wait(seconds):
        if seconds==.08:geometry["left"]=20
    monkeypatch.setattr("games.mahjong_soul.live.runtime.windows_input.time.sleep",wait)
    with pytest.raises(ValueError,match="moved or resized"):m.double_click(.5,.5,1920,1080)
    assert [t[1] for t in trace if t[0]=="event"]==[0xc001,0xc003,4]
