"""Recorded Chi menu regression: smaller faces and the real opening animation."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import zlib
import pytest
from agents.mahjong_soul.auto import AutoFollower
from games.mahjong_soul.live.runtime.call_selection import plan_call,plan_call_choice
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.visual import TileVision
from tests.mahjong_soul.test_auto import Mouse


def fixture(monkeypatch):
    f=json.loads((Path(__file__).parent/"fixtures/visual_chi_choices.json").read_text(encoding="utf-8"))
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]))
        rgb=bytearray(1920*1080*3)
        for row in range(h):rgb[((y+row)*1920+x)*3:((y+row)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f["report"]


@pytest.mark.parametrize("combination,pixel_x",[("1s|3s",841),("3s|4s",1041)])
def test_recorded_menu_binds_both_exact_contributions_at_real_scale(monkeypatch,combination,pixel_x):
    report=fixture(monkeypatch);action={"kind":"chi","combination":combination}
    for frame in (b"stable1",b"stable2"):
        profile,_=TileVision().choices(frame,report,action)
        assert profile["combinations"]==["1s|3s","3s|4s"]
        plan=plan_call_choice(report,profile,action,now=1)
        assert plan.tiles[:2]==tuple(combination.split("|"))
        assert round(plan.x*1919)==pixel_x and round(plan.y*1079)==770


def test_opening_animation_is_refused_until_whole_panel_is_visible(monkeypatch):
    report=fixture(monkeypatch)
    with pytest.raises(ValueError,match="whole call choice panel"):
        TileVision().choices(b"animated",report,{"kind":"chi","combination":"3s|4s"})


def test_saved_menu_continues_through_native_controller_and_exact_confirmation(monkeypatch):
    report=fixture(monkeypatch);action={"kind":"chi","combination":"3s|4s"}
    images=iter([b"stable1",b"stable2"])
    class Recorder:
        def geometry(self):return {"width":1920,"height":1080,"left":0,"top":0}
        def frame(self,geometry):return next(images)
    mouse=Mouse();controller=InputController(mouse)
    follower=AutoFollower(None,file="unused",controller=controller,recorder=Recorder(),vision=TileVision(),clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:deepcopy(report)
    menu=plan_call(report,{"version":1,"verified":True,"stage":"call_offer","client_size":[1920,1080],"operation_types":[2],"chi":[1020/1919,835/1079]},action,now=1)
    controller.submit(menu,report,enabled=True,now=1)
    follower.call_pending=action,menu.token
    follower._continue_call()
    assert len(mouse.clicks)==2 and round(mouse.clicks[-1][0]*1919)==1041
    assert follower.call_pending is None
    assert controller.snapshot()["attempted_steps"]==1
    event={"source":"live","name":"ActionChiPengGang","step":menu.step+1,
           "data":{"seat":2,"type":0,"tiles":["3s","4s","2s"],"froms":[2,2,1]}}
    assert controller.observe(report["game_connection"],event,now=2)
    assert controller.snapshot()["status"]=="idle"
