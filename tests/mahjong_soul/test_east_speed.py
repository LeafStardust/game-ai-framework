from copy import deepcopy
from agents.mahjong_soul.attack_policy import offensive
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from games.mahjong_soul.live.runtime.lobby import detect_lobby
from tests.mahjong_soul.test_attack_v2 import report,call_report,choose,board


def east(r):
    r["state"]["lobby"]=detect_lobby({"seat_list":[0,1,2,3],"game_config":{"mode":{"mode":1}}})
    return r


def test_east_routes_automatically_and_south_settings_remain_unchanged():
    registry=default_mahjong_playbooks();south=registry.get(4,"atk","south");before=deepcopy(south.strategy)
    action,analysis=choose(east(report("123m456p789s11z99p2z")))
    assert analysis["playbook"]=="4 Player East Wind Speed" and analysis["style"]=="speed"
    assert south.strategy==before and south.strategy["defense"]["always_push"]
    assert south.strategy["calls"]["minimum_han"]==3


def test_speed_then_defense_then_value_order():
    settings=default_mahjong_playbooks().get(4,"atk","east").thresholds_for("D1")
    def option(tile,distance,copies,risk,han):
        return {"action":{"kind":"discard","tile":tile},"shanten":distance,"effective_ukeire":copies,
                "danger":risk,"total_danger":risk,"projected_han":han,"route_cost":0,"wait_value":None}
    fast=option("1m",1,20,90,1);valuable=option("2m",1,19,0,8);safe=option("3m",1,20,0,1)
    assert offensive(board("123m456p789s11z99p2z"),[fast,valuable],settings) is fast
    assert offensive(board("123m456p789s11z99p2z"),[fast,valuable,safe],settings) is safe
    closer=option("4m",0,2,90,1)
    assert offensive(board("123m456p789s11z99p2z"),[fast,closer],settings) is closer


def test_east_can_open_for_one_han_when_it_accelerates_a_legal_win():
    r=east(call_report("55z123m456p78s22p9m","5z","5z|5z"))
    action,analysis=choose(r)
    assert action["kind"]=="pon" and analysis["shanten"]==0
    assert analysis["projected_han"]>=1


def test_east_folds_distant_hand_against_multiple_riichi():
    r=east(report("147m258p369s12345z"))
    r["state"]["riichi"][1:3]=["accepted","accepted"]
    r["state"]["discards"][1]=[{"tile":"1z","called":False}]
    r["state"]["discards"][2]=[{"tile":"1z","called":False}]
    action,analysis=choose(r)
    assert analysis["mode"]=="fold" and action["tile"]=="1z"
