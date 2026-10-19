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
    f=json.loads((Path(__file__).parent/"fixtures/attack_yaku_routes.json").read_text())
    frames={};x,y,w,h=f["crop"]
    for name,entry in f["frames"].items():
        crop=zlib.decompress(base64.b64decode(entry["rgb_zlib"]));rgb=bytearray(1920*1080*3)
        for r in range(h):rgb[((y+r)*1920+x)*3:((y+r)*1920+x+w)*3]=crop[r*w*3:(r+1)*w*3]
        frames[name.encode()]=rgb
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda key:frames[key])
    return f


def test_recorded_three_choice_sou_panel_recognizes_all_combinations(monkeypatch):
    from games.mahjong_soul.live.runtime.call_selection import plan_call_choice
    f=fixture(monkeypatch);r=f["frames"]["heldout"]["report"]
    for combo in ("5s|6s","6s|8s","8s|9s"):
        action={"kind":"chi","combination":combo}
        profile,_=TileVision().choices(b"heldout",r,action)
        assert set(profile["combinations"])=={"5s|6s","6s|8s","8s|9s"}
        assert plan_call_choice(r,profile,action,now=1).tiles[:2]==tuple(combo.split("|"))


def test_recorded_calls_do_not_borrow_progress_from_yaku_incompatible_tiles(monkeypatch):
    f=fixture(monkeypatch)
    for index in (0,3):assert choose(f["reports"][index])[0]["kind"]=="skip"


def test_recorded_opponent_riichi_does_not_change_attack_into_fold(monkeypatch):
    from copy import deepcopy
    f=fixture(monkeypatch)
    for r in f["reports"]:
        original,analysis=choose(r)
        no_threat=deepcopy(r);no_threat["state"]["riichi"]=["none"]*4
        assert choose(no_threat)[0]==original
        assert analysis["mode"]!="fold"


def test_explicit_regular_distance_agrees_with_standard_shapes():
    import random
    from mahjong.shanten import Shanten
    from agents.mahjong_soul.attack_routes import _regular_distance
    rng=random.Random(23)
    for fixed in range(4):
        for _ in range(20):
            pool=[i for i in range(34) for _ in range(4)];hand=rng.sample(pool,13-3*fixed)
            counts=tuple(hand.count(i) for i in range(34))
            assert _regular_distance(counts,fixed)==Shanten.calculate_shanten_for_regular_hand(counts)


def test_open_hand_discards_advance_the_selected_yaku_instead_of_yakuless_speed(monkeypatch):
    f=fixture(monkeypatch)
    action,analysis=choose(f["reports"][1])
    assert action=={"kind":"discard","tile":"9m"}
    assert analysis["target_route"]=="honitsu"
    assert {t["tile"] for t in analysis["improving_tiles"]}=={"6s","1z"}
    action,analysis=choose(f["reports"][4])
    assert action["tile"]=="9p" and analysis["target_route"]=="tanyao"
    assert all(t["tile"][1]!="z" and 2<=int(t["tile"][0])<=8 for t in analysis["improving_tiles"])
