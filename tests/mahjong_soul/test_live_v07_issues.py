import base64
import json
import zlib
from copy import deepcopy
from pathlib import Path
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision
from tests.mahjong_soul.test_attack_v2 import choose


def fixture():
    return json.loads((Path(__file__).parent/"fixtures/live_v07_issues.json").read_text())


def test_recorded_two_copy_kokushi_keeps_dama():
    report=fixture()["kokushi_report"];before=deepcopy(report)
    action,analysis=choose(report)
    assert action=={"kind":"discard","tile":"6s"}
    assert analysis["wait_value"]["dama_points"]==32000
    assert report==before


def test_reviewed_red_sou_sample_recognized_without_reader_hint():
    vision=TileVision()
    assert vision.classify(base64.b64decode(fixture()["red_sou_sample"]))=="0s"


def test_recorded_three_button_pon_layout(monkeypatch):
    crop=fixture()["pon_crop"];x,y,w,h=crop["bounds"]
    data=zlib.decompress(base64.b64decode(crop["rgb_zlib"]))
    rgb=bytearray(1920*1080*3)
    for j in range(h):
        rgb[((y+j)*1920+x)*3:((y+j)*1920+x+w)*3]=data[j*w*3:(j+1)*w*3]
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:rgb)
    vision=TileVision()
    assert vision.button(b"frame","pon")[:2]==(730,835)
    for kind in ("chi","skip","extract_north"):
        with pytest.raises(ValueError):vision.button(b"frame",kind)
