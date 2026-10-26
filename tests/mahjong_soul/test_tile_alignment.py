import base64
from copy import deepcopy
import json
from pathlib import Path
import zlib
import pytest
from agents.mahjong_soul.auto import AutoFollower
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.layout import discard_profile
from games.mahjong_soul.live.runtime.visual import TileVision,sample
from tests.mahjong_soul.test_auto import Mouse


def fixture(monkeypatch):
    f=json.loads((Path(__file__).parent/"fixtures/visual_tile_alignment.json").read_text(encoding="utf-8"));frames={}
    x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]))
        rgb=bytearray(1920*1080*3)
        for row in range(h):rgb[((row+y)*1920+x)*3:((row+y)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f,frames


def test_recorded_eight_sou_stall_is_fixed_without_lowering_thresholds(monkeypatch):
    f,frames=fixture(monkeypatch)
    for name in ("stable1","stable2"):
        r=f["frames"][name]["report"];profile=discard_profile(r,(1920,1080));vision=TileVision()
        x,y=profile["slots"][5]
        with pytest.raises(ValueError):vision.classify(sample(frames[name.encode()],round(x*1919),round(y*1079)))
        tiles,_=vision.hand(name.encode(),profile,r["state"]["hand"])
        assert tiles==["0m","4p","9p","0s","6s","8s","8s","9s"]
        assert vision.last_diagnostics["slots"][5]["sampling_offset"]==[0,-2]
        assert vision.MAX_DISTANCE==10 and vision.MIN_MARGIN==4


def test_real_hand_preflight_and_discard_confirmation_with_fake_mouse(monkeypatch):
    f,_=fixture(monkeypatch);report=f["frames"]["stable1"]["report"];images=iter([b"stable1",b"stable2"])
    class Recorder:
        def geometry(self):return {"width":1920,"height":1080,"left":0,"top":0}
        def frame(self,geometry):return next(images)
    mouse=Mouse();controller=InputController(mouse)
    follower=AutoFollower(None,file="unused",controller=controller,recorder=Recorder(),vision=TileVision(),clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:deepcopy(report)
    plan,current=follower._plan({"board_token":board_token(report),"action":{"kind":"discard","tile":"9s"}})
    assert plan.tile=="9s" and round(plan.x*1919)==935
    controller.submit(plan,current,enabled=True,now=1)
    assert len(mouse.clicks)==1
    assert controller.observe(report["game_connection"],{"name":"ActionDiscardTile","source":"live","step":plan.step+1,"data":{"seat":plan.seat,"tile":"9s"}},now=2)


def test_settings_dialog_does_not_become_a_valid_hand(monkeypatch):
    f,_=fixture(monkeypatch);r=f["frames"]["dialog"]["report"]
    with pytest.raises(ValueError):TileVision().hand(b"dialog",discard_profile(r,(1920,1080)),r["state"]["hand"])


def test_alignment_disagreement_is_rejected_instead_of_guessing_from_reader(monkeypatch):
    vision=TileVision()
    def sampled(rgb,x,y):return bytes([1 if (x,y)==(100,98) else 2 if (x,y)==(100,102) else 0])*648
    def classify(value):
        if value[0]==1:return "0s"
        if value[0]==2:return "5s"
        raise ValueError("Unknown")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",sampled)
    monkeypatch.setattr(vision,"classify",classify)
    with pytest.raises(ValueError,match="disagree"):vision.align_tile(b"rgb",100,100,"Unknown")


def test_selected_lift_is_only_available_for_explicit_retry(monkeypatch):
    vision=TileVision()
    def sampled(rgb,x,y):return bytes([1 if (x,y)==(100,52) else 0])*648
    def classify(value):
        if value[0]==1:return "2z"
        raise ValueError("Unknown")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",sampled)
    monkeypatch.setattr(vision,"classify",classify)
    with pytest.raises(ValueError):vision.align_tile(b"rgb",100,100,"Unknown")
    tile,value,offset=vision.align_tile(b"rgb",100,100,"Unknown",selected_retry=True)
    assert tile=="2z" and offset==(0,-48)


def test_selected_retry_does_not_override_disagreeing_tile_identity(monkeypatch):
    vision=TileVision()
    def sampled(rgb,x,y):return bytes([1 if (x,y)==(100,52) else 2 if (x,y)==(100,98) else 0])*648
    def classify(value):
        if value[0]==1:return "2z"
        if value[0]==2:return "3z"
        raise ValueError("Unknown")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",sampled)
    monkeypatch.setattr(vision,"classify",classify)
    with pytest.raises(ValueError,match="disagree"):
        vision.align_tile(b"rgb",100,100,"Unknown",selected_retry=True)
