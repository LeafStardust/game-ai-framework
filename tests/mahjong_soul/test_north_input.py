import base64,json,zlib
from pathlib import Path
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision
from games.mahjong_soul.live.runtime.north import plan_north
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_input import Mouse


def fixture(monkeypatch,name="north_offer.json"):
    data=json.loads((Path(__file__).parent/"fixtures"/name).read_text());frames={}
    x,y,w,h=data["crop"]
    for i,entry in enumerate(data["frames"]):
        rgb=bytearray(1920*1080*3);crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]))
        for row in range(h):rgb[((y+row)*1920+x)*3:((y+row)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
        frames[str(i).encode()]=rgb
    frames[b"blank"]=bytes(1920*1080*3)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return data


def test_recorded_north_offer_recognition_and_correlated_confirmation(monkeypatch):
    f=fixture(monkeypatch);vision=TileVision();report=f["frames"][1]["report"]
    for frame in (b"0",b"1"):
        x,y,_=vision.button(frame,"extract_north")
        assert (x,y)==(1020,835)
    with pytest.raises(ValueError):vision.button(b"blank","extract_north")
    profile={"version":1,"verified":True,"stage":"call_offer","client_size":[1920,1080],
             "operation_types":[1,11],"extract_north":[x/1919,y/1079]}
    plan=plan_north(report,profile,now=1);mouse=Mouse();controller=InputController(mouse)
    controller.submit(plan,report,enabled=True,now=1)
    assert len(mouse.clicks)==1
    event={"name":"ActionBaBei","source":"live","step":plan.step+1,"data":{"seat":plan.seat}}
    assert not controller.observe("wrong",event,now=1)
    assert not controller.observe(plan.connection,{**event,"source":"restore"},now=1)
    assert not controller.observe(plan.connection,{**event,"data":{"seat":(plan.seat+1)%3}},now=1)
    assert controller.observe(plan.connection,event,now=1)
    with pytest.raises(ValueError):controller.submit(plan,report,enabled=True,now=1)


def test_north_requires_matching_offer_and_calibration(monkeypatch):
    f=fixture(monkeypatch);report=f["frames"][0]["report"]
    with pytest.raises(ValueError):plan_north(report,{"verified":False},now=1)


def test_runner_builds_north_plan_from_two_visual_checks_without_input(monkeypatch):
    from tests.mahjong_soul.test_auto import setup
    from games.mahjong_soul.live.runtime.input import board_token
    from games.mahjong_soul.live.runtime.north import NorthPlan
    f,_,_,_,mouse=setup(monkeypatch)
    data=fixture(monkeypatch);report=data["frames"][0]["report"]
    f._current=lambda:report;f.recorder.frame=lambda _:b"0";f.vision=TileVision();f.sleep=lambda _:None
    plan,current=f._plan({"board_token":board_token(report),"action":{"kind":"extract_north","tile":"4z"}})
    assert isinstance(plan,NorthPlan) and current==report and not mouse.clicks


def test_kita_and_kan_offer_uses_shifted_north_label(monkeypatch):
    from tests.mahjong_soul.test_auto import setup
    from games.mahjong_soul.live.runtime.input import board_token
    f,_,_,_,mouse=setup(monkeypatch)
    data=fixture(monkeypatch,"north_kan_offer.json");vision=TileVision()
    for frame in (b"0",b"1"):
        x,y,_=vision.button(frame,"extract_north")
        assert (x,y)==(730,835)
    report=data["frames"][1]["report"]
    f._current=lambda:report;f.recorder.frame=lambda _:b"1";f.vision=vision;f.sleep=lambda _:None
    plan,_=f._plan({"board_token":board_token(report),"action":{"kind":"extract_north","tile":"4z"}})
    assert round(plan.x*1919)==730 and not mouse.clicks
    with pytest.raises(ValueError):vision.button(b"blank","extract_north")
