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
    f=json.loads((Path(__file__).parent/"fixtures/visual_six_sou.json").read_text())
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]));rgb=bytearray(1920*1080*3)
        for r in range(h):rgb[((y+r)*1920+x)*3:((y+r)*1920+x+w)*3]=crop[r*w*3:(r+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f


def test_held_out_six_sou_hand_passes_without_lowering_confidence(monkeypatch):
    f=fixture(monkeypatch)
    for name in ("1693","1697"):
        r=f["frames"][name]["report"];v=TileVision()
        tiles,_=v.hand(name.encode(),discard_profile(r,(1920,1080)),r["state"]["hand"])
        assert tiles[2:5]==["6s"]*3
        assert v.MAX_DISTANCE==10 and v.MIN_MARGIN==4


def test_afk_dialog_remains_blocked(monkeypatch):
    f=fixture(monkeypatch);r=f["frames"]["2253"]["report"]
    with pytest.raises(ValueError):
        TileVision().hand(b"2253",discard_profile(r,(1920,1080)),r["state"]["hand"])


def test_recorded_discard_preflight_works_with_fake_mouse(monkeypatch):
    f=fixture(monkeypatch);r=f["frames"]["1693"]["report"];images=iter([b"1693",b"1697"])
    class Recorder:
        def geometry(self):return {"width":1920,"height":1080,"left":0,"top":0}
        def frame(self,geometry):return next(images)
    mouse=Mouse();follower=AutoFollower(None,file="unused",controller=InputController(mouse),recorder=Recorder(),vision=TileVision(),clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:r
    plan,_=follower._plan({"board_token":board_token(r),"action":{"kind":"discard","tile":"4z"}})
    assert plan.tile=="4z" and mouse.clicks==[]
