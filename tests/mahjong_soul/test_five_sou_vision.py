"""Recorded East Three Honitsu regressions; no native inputs."""
import base64
import json
from pathlib import Path
import zlib
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision
from games.mahjong_soul.live.runtime.layout import discard_profile
from games.mahjong_soul.live.runtime.input import board_token
from agents.mahjong_soul.auto import AutoFollower
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_auto import Mouse
from tests.mahjong_soul.test_attack_v2 import choose


def fixture(monkeypatch):
    f=json.loads((Path(__file__).parent/"fixtures/visual_five_sou.json").read_text())
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]));rgb=bytearray(1920*1080*3)
        for r in range(h):rgb[((y+r)*1920+x)*3:((y+r)*1920+x+w)*3]=crop[r*w*3:(r+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f


def test_recorded_five_sou_frames_recognize_whole_hands(monkeypatch):
    f=fixture(monkeypatch)
    for name,entry in f["frames"].items():
        r=entry["report"];v=TileVision()
        tiles,_=v.hand(name.encode(),discard_profile(r,(1920,1080)),r["state"]["hand"])
        assert tiles[:4]==["3s","3s","5s","7s"]
        assert v.MAX_DISTANCE==10 and v.MIN_MARGIN==4
        wrong=["0s" if t=="5s" else t for t in r["state"]["hand"]]
        with pytest.raises(ValueError,match="differs from reader"):
            v.hand(name.encode(),discard_profile(r,(1920,1080)),wrong)


def test_recorded_stalled_discard_passes_both_visual_checks_with_fake_mouse(monkeypatch):
    f=fixture(monkeypatch);r=f["frames"]["1059"]["report"];images=iter([b"1059",b"1065"])
    class Recorder:
        def geometry(self):return {"width":1920,"height":1080,"left":0,"top":0}
        def frame(self,geometry):return next(images)
    mouse=Mouse();follower=AutoFollower(None,file="unused",controller=InputController(mouse),recorder=Recorder(),vision=TileVision(),clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:r
    plan,_=follower._plan({"board_token":board_token(r),"action":{"kind":"discard","tile":"2z"}})
    assert plan.tile=="2z"
    assert mouse.clicks==[]
