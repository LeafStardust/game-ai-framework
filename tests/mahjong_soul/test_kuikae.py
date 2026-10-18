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
    f=json.loads((Path(__file__).parent/"fixtures/visual_kuikae.json").read_text())
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]));rgb=bytearray(1920*1080*3)
        for r in range(h):rgb[((y+r)*1920+x)*3:((y+r)*1920+x+w)*3]=crop[r*w*3:(r+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f


def test_recorded_equal_value_calls_do_not_shrink_honitsu_wait(monkeypatch):
    f=fixture(monkeypatch)
    action,analysis=choose(f["calls"][0])
    assert action["kind"]=="skip"
    assert any(n["rejections"].get("no_ready_hand_improvement",0) for n in analysis["call_evaluations"])
    # After the actual timeout discarded 3 Man, a later Chi restored Tenpai.
    # That recovery call is useful and must remain allowed.
    assert choose(f["calls"][1])[0]["kind"]=="chi"


def test_dimmed_six_man_requires_explicit_server_restriction(monkeypatch):
    f=fixture(monkeypatch);r=f["frames"]["939"]["report"];profile=discard_profile(r,(1920,1080));vision=TileVision()
    with pytest.raises(ValueError):vision.hand(b"939",profile,r["state"]["hand"])
    profile["forbidden_tiles"]=["6m"]
    assert vision.hand(b"939",profile,r["state"]["hand"])[0]==["1m","1m","2m","3m","6m"]
    profile["forbidden_tiles"]=["7m"]
    with pytest.raises(ValueError):vision.hand(b"939",profile,r["state"]["hand"])


def test_post_call_preflight_recognizes_dimmed_forbidden_tile_without_clicking_it(monkeypatch):
    f=fixture(monkeypatch);report=f["frames"]["939"]["report"];images=iter([b"939",b"943"])
    class Recorder:
        def geometry(self):return {"width":1920,"height":1080,"left":0,"top":0}
        def frame(self,geometry):return next(images)
    mouse=Mouse();follower=AutoFollower(None,file="unused",controller=InputController(mouse),recorder=Recorder(),vision=TileVision(),clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:report
    plan,_=follower._plan({"board_token":board_token(report),"action":{"kind":"discard","tile":"1m"}})
    assert plan.tile=="1m"
    assert mouse.clicks==[]
