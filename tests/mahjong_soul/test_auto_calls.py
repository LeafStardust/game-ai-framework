from copy import deepcopy
import pytest

from agents.mahjong_soul.auto_policy import AutomaticPolicy
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.visual import TileVision, sample
from tests.mahjong_soul.test_auto import setup
from tests.mahjong_soul.test_calls import offer


def test_automatic_policy_rechooses_without_unsupported_calls_or_mutating_request():
    class Policy:
        last_analysis = {"value": 4}
        def choose(self, request):
            assert [a["kind"] for a in request["actions"]] == ["skip"]
            return request["actions"][0]
    request = {"actions": [{"kind":"pon","combination":"0p|5p"},
                            {"kind":"pon","combination":"5p|5p"},
                            {"kind":"open_kan","combination":"0p|5p|5p"},
                            {"kind":"skip"}]}
    original=deepcopy(request)
    policy=AutomaticPolicy(Policy())
    assert policy.choose(request)=={"kind":"skip"}
    assert request==original
    assert len(policy.last_analysis["automatic_omitted_actions"])==3


def test_automatic_policy_preserves_single_call_and_win():
    class Policy:
        def choose(self, request):
            assert len(request["actions"])==2
            return request["actions"][1]
    actions=[{"kind":"chi","combination":"1m|2m"},{"kind":"ron"}]
    assert AutomaticPolicy(Policy()).choose({"actions":actions})==actions[1]


def test_automatic_pon_uses_native_controller_and_exact_server_confirmation(monkeypatch):
    follower,_,_,_,mouse=setup(monkeypatch)
    report,_=offer()
    follower._current=lambda:deepcopy(report)
    event={"board_token":board_token(report),"action":{"kind":"pon","combination":"0p|5p"}}
    plan,current=follower._plan(event)
    follower.controller.submit(plan,current,enabled=True,now=1)
    assert len(mouse.clicks)==1
    assert follower.controller.snapshot()["status"]=="awaiting_confirmation"
    confirmation={"name":"ActionChiPengGang","source":"live","step":1,
                  "data":{"seat":0,"type":1,"tiles":["0p","5p","5p"],"froms":[0,0,3]}}
    assert follower.controller.observe("game",confirmation,now=2)
    assert follower.controller.snapshot()["status"]=="idle"


def test_wrong_selected_combination_never_clicks(monkeypatch):
    follower,_,_,_,mouse=setup(monkeypatch)
    report,_=offer();follower._current=lambda:deepcopy(report)
    event={"board_token":board_token(report),"action":{"kind":"pon","combination":"5p|5p"}}
    with pytest.raises(ValueError,match="exact server combination"):follower._plan(event)
    assert not mouse.clicks


@pytest.mark.parametrize("kind",["chi","pon"])
def test_call_button_templates_bind_position_and_reject_wrong_label(monkeypatch,kind):
    import games.mahjong_soul.live.runtime.visual as visual
    vision=TileVision()
    monkeypatch.setattr(visual,"decode_frame",lambda _:b"pixels")
    def sampled(rgb,x,y,width,height):
        return vision.calls[kind] if x==750 else bytes(648)
    monkeypatch.setattr(visual,"sample",sampled)
    assert vision.button(b"frame",kind)[:2]==(750,835)
    with pytest.raises(ValueError,match="not uniquely visible"):
        vision.button(b"frame","pon" if kind=="chi" else "chi")
    monkeypatch.setattr(visual,"sample",lambda *args:vision.calls[kind])
    with pytest.raises(ValueError,match="not uniquely visible"):vision.button(b"frame",kind)


def test_unknown_button_cannot_use_win_color_detector():
    with pytest.raises(ValueError):TileVision().button(b"invalid","kan")


def test_automatic_chi_confirms_exact_contributions(monkeypatch):
    follower,_,_,_,mouse=setup(monkeypatch)
    report,_=offer()
    report["state"]["hand"]=["1p","2p"]
    report["state"]["discards"][3]=[{"tile":"3p","called":False}]
    report["state"]["operations"]["operation_list"]=[{"type":2,"combination":["1p|2p"]}]
    follower._current=lambda:deepcopy(report)
    event={"board_token":board_token(report),"action":{"kind":"chi","combination":"1p|2p"}}
    plan,current=follower._plan(event)
    follower.controller.submit(plan,current,enabled=True,now=1)
    assert len(mouse.clicks)==1
    confirmation={"name":"ActionChiPengGang","source":"live","step":1,
                  "data":{"seat":0,"type":0,"tiles":["1p","2p","3p"],"froms":[0,0,3]}}
    assert follower.controller.observe("game",confirmation,now=2)
    assert follower.controller.snapshot()["status"]=="idle"
