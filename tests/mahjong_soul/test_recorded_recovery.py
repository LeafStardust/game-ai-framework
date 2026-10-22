import base64,json,zlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from agents.mahjong_soul.auto import AutoFollower
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import DiscardPlan
from games.mahjong_soul.live.runtime.visual import TileVision


def case():
    return json.loads((Path(__file__).parent/"fixtures/recorded_focus_recovery.json").read_text())


def pixels(frame):
    rgb=bytearray(1920*1080*3)
    for patch in frame["patches"]:
        x,y,w,h=patch["bounds"];raw=zlib.decompress(base64.b64decode(patch["rgb_zlib"]))
        for j in range(h):rgb[((y+j)*1920+x)*3:((y+j)*1920+x+w)*3]=raw[j*w*3:(j+1)*w*3]
    return rgb


@pytest.mark.parametrize("guard",[None,"unverified_room","background","stale"])
@pytest.mark.parametrize("index,expected",[(0,False),(1,True),(2,False)])
def test_actual_focus_incident_recovery_through_real_hand_recognition(monkeypatch,index,expected,guard):
    data=case();frame=data["frames"][index];rgb=pixels(frame)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:rgb)
    class Mouse:
        def __init__(self):self.attempts=0
        def double_click(self,*args):
            self.attempts+=1
            raise ValueError("Mahjong Soul is not the foreground window")
    mouse=Mouse();controller=InputController(mouse)
    initial=data["initial_report"];plan=replace(DiscardPlan(**data["plan"]),expires=2)
    with pytest.raises(ValueError):controller.submit(plan,initial,enabled=True,now=1)
    report=deepcopy(frame["report"])
    follower=AutoFollower(None,file="unused",controller=controller,recorder=SimpleNamespace(
        geometry=lambda:{"width":1920,"height":1080,"left":0,"top":0},frame=lambda _:b"frame"),
        vision=TileVision(),enabled=True,clock=lambda:1,sleep=lambda _:None,require_ai=True)
    follower.reader=SimpleNamespace(snapshot=lambda:deepcopy(report));follower._current=lambda:deepcopy(report)
    follower.ai_games.add((report["game_connection"],report["game_generation"]))
    follower.halted="Mahjong Soul is not the foreground window"
    if guard=="unverified_room":follower.ai_games.clear()
    if guard=="background":follower.recorder.geometry=lambda:None
    if guard=="stale":
        def stale():raise ValueError("Capture became stale")
        follower._current=stale
    expected=expected and guard is None
    assert follower._recover_advanced_input()==expected
    assert mouse.attempts==1  # Recovery itself never delivers another input.
    assert controller.was_attempted(initial,plan.step)
    assert (controller.snapshot()["status"]=="idle")==expected


def test_recorded_settings_overlay_rejected_while_board_passes(monkeypatch):
    data=case();vision=TileVision()
    for index in (1,2):
        rgb=pixels(data["frames"][index])
        if index==1:vision.require_gameplay(b"frame",rgb=rgb)
        else:
            with pytest.raises(ValueError,match="settings overlay"):vision.require_gameplay(b"frame",rgb=rgb)
