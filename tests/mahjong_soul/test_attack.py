from copy import deepcopy
import pytest
from agents.mahjong_soul.playbook_policy import PlaybookPolicy
from agents.mahjong_soul.evaluate import decide
from games.mahjong_soul.live.runtime.decision import decision_request
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from tests.mahjong_soul.test_efficiency import request
from tests.mahjong_soul.test_win_input import offer as win_offer


def board():
    q,report = request("12m",4)
    report["state"]["round"] = {"chang":0,"ju":0}
    report["state"]["left_tile_count"] = 30
    report["state"]["furiten"] = False
    return report


def mock_rank(monkeypatch, distance=2, ukeire=(20,20), second_distance=None):
    from agents.mahjong_soul import playbook_policy as module
    options=[{"action":{"kind":"discard","tile":"1m"},"shanten":distance,"ukeire":ukeire[0],"improving_tiles":[]},
             {"action":{"kind":"discard","tile":"2m"},"shanten":distance if second_distance is None else second_distance,
              "ukeire":ukeire[1],"improving_tiles":[]}]
    monkeypatch.setattr(module,"rank_discards",lambda request:deepcopy(options))


def threat(report, seat=1):
    report["state"]["riichi"][seat] = "accepted"
    report["state"]["discards"][seat] = [{"tile":"2m","called":False}]


def test_only_four_player_atk_is_registered_and_balanced_still_resolves():
    registry=default_mahjong_playbooks()
    assert registry.get(4,"atk").name == "Four-Player South Attack"
    assert registry.get(4).style == registry.get(3).style == "balanced"
    with pytest.raises(LookupError):registry.get(3,"atk")
    report=board();report["state"]["player_count"]=3
    from games.mahjong_soul.playbook.model import UnsupportedLobby
    with pytest.raises(UnsupportedLobby):decide(PlaybookPolicy(style="atk"),report,lambda:report)


def test_attack_recomputes_real_route_progress_instead_of_trusting_mocked_distance(monkeypatch):
    report=board();report["state"]["doras"]=["9m"]  # Dora is 1 Man.
    # Mixed fixed suits prevent a flush target that must shed this Dora.
    report["state"]["melds"][0][0]["tiles"]=["3s"]*3
    mock_rank(monkeypatch,distance=1,ukeire=(20,17))
    assert decide(PlaybookPolicy(),report,lambda:report)["action"]["tile"] == "1m"
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]["tile"] == "2m"
    mock_rank(monkeypatch,distance=1,ukeire=(20,13))
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]["tile"] == "2m"
    mock_rank(monkeypatch,distance=1,ukeire=(20,100),second_distance=2)
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]["tile"] == "2m"


def test_attack_pushes_value_with_yakuhai_route_but_balanced_folds(monkeypatch):
    report=board();threat(report)
    # Own fixed triplet of 3 Pin becomes dora and a white-dragon triplet provides a scoring route.
    report["state"]["doras"]=["2p"]
    report["state"]["melds"][0][1]["tiles"]=["5z"]*3
    mock_rank(monkeypatch,distance=2,ukeire=(20,19))
    assert decide(PlaybookPolicy(),report,lambda:report)["action"]["tile"] == "2m"
    policy=PlaybookPolicy(style="atk")
    action=decide(policy,report,lambda:report)["action"]
    assert policy.last_analysis["mode"] == "attack_push"
    no_threat=deepcopy(report);no_threat["state"]["riichi"][1]="none"
    assert decide(PlaybookPolicy(style="atk"),no_threat,lambda:no_threat)["action"]==action
    assert policy.last_analysis["retained_value_proxy"] >= 3


@pytest.mark.parametrize("block",["low_value","no_yaku_route","late_wall","two_threats","distant"])
def test_attack_keeps_pushing_instead_of_switching_to_defense(block,monkeypatch):
    report=board();threat(report);report["state"]["doras"]=["2p"]
    report["state"]["melds"][0][1]["tiles"]=["5z"]*3
    distance=2
    if block=="low_value":report["state"]["doras"]=[]
    if block=="no_yaku_route":
        report["state"]["melds"][0][1]["tiles"]=["4p"]*3
        report["state"]["melds"][0][0]={"type":0,"tiles":["1s","2s","3s"]}
    if block=="late_wall":report["state"]["left_tile_count"]=5
    if block=="two_threats":threat(report,2)
    if block=="distant":distance=3
    mock_rank(monkeypatch,distance=distance)
    policy=PlaybookPolicy(style="atk")
    assert decide(policy,report,lambda:report)["action"]["tile"]=="2m"
    assert policy.last_analysis["mode"]=="attack_push"


def closed_riichi_report(report):
    from tests.mahjong_soul.test_efficiency import tiles
    report["state"]["hand"]=tiles("123m123p123s777z12m")
    report["state"]["melds"][0]=[]
    return report


def test_attack_can_counter_riichi_on_good_wait_while_balanced_stays_undeclared(monkeypatch):
    report=closed_riichi_report(board());threat(report);mock_rank(monkeypatch,distance=0,ukeire=(8,4))
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["1m"]})
    assert decide(PlaybookPolicy(),report,lambda:report)["action"]["kind"]=="discard"
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]=={"kind":"riichi","tile":"1m"}


@pytest.mark.parametrize("block",["poor_wait","furiten","unknown_furiten","late_wall","two_threats"])
def test_attack_counter_riichi_constraints(block,monkeypatch):
    report=closed_riichi_report(board());threat(report);wait=8
    if block=="poor_wait":wait=4
    if block=="furiten":report["state"]["furiten"]=True
    if block=="unknown_furiten":report["state"]["furiten"]=None
    if block=="late_wall":report["state"]["left_tile_count"]=4
    if block=="two_threats":threat(report,2)
    mock_rank(monkeypatch,distance=0,ukeire=(wait,4))
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["1m"]})
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]["kind"]==("discard" if block in ("furiten","unknown_furiten") else "riichi")


def test_attack_still_takes_offered_wins_first():
    report,_=win_offer()
    assert decide(PlaybookPolicy(style="atk"),report,lambda:report)["action"]["kind"]=="tsumo"
