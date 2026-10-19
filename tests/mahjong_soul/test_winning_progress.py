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
    f=json.loads((Path(__file__).parent/"fixtures/winning_progress.json").read_text())
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]));rgb=bytearray(1920*1080*3)
        for r in range(h):rgb[((y+r)*1920+x)*3:((y+r)*1920+x+w)*3]=crop[r*w*3:(r+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f


def test_recorded_chi_button_is_recognized_at_actual_location(monkeypatch):
    fixture(monkeypatch)
    assert TileVision().button(b"heldout","chi")[:2]==(750,835)
    assert TileVision().button(b"heldout","pon")[:2]==(1020,835)


def test_recorded_first_round_takes_available_tenpai_instead_of_value_chase(monkeypatch):
    f=fixture(monkeypatch);action,analysis=choose(f["reports"]["392"])
    assert action=={"kind":"discard","tile":"1s"}
    assert analysis["shanten"]==0 and analysis["effective_ukeire"]>0


def test_recorded_route_han_is_not_borrowed_from_an_unrelated_fast_shape(monkeypatch):
    f=fixture(monkeypatch)
    for key in ("26","98","256","423"):
        _,analysis=choose(f["reports"][key])
        assert analysis["target_route"]!="honitsu"
        assert analysis["target_route"]!="toitoi"


def test_recorded_same_shanten_call_cannot_throw_away_most_improving_draws(monkeypatch):
    f=fixture(monkeypatch);action,analysis=choose(f["reports"]["549"])
    assert action["kind"]=="skip"
    assert any(n["rejections"].get("call_reduces_winning_chances") for n in analysis["call_evaluations"])
