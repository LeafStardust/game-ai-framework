from copy import deepcopy
import pytest
from agents.mahjong_soul.attack_routes import project_attack,known_bonus
from agents.mahjong_soul.attack_policy import offensive
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from tests.mahjong_soul.test_attack_v2 import report,board,call_report,choose


def test_recorded_red_five_chi_does_not_invent_han_from_terminal_dora_the_route_must_discard():
    r=call_report("0m1m1p1p1s2m2p4m6m6p7s8m8p","4m","0m|6m",2,doras=["9p"])
    before=deepcopy(r);action,analysis=choose(r)
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["accepted"] is False
    assert r==before



@pytest.mark.parametrize("threat_count",[0,1,3])
def test_value_pon_builds_reachable_yakuhai_even_through_multiple_threats(threat_count):
    r=call_report("11m22p33s55z67m89s9p","1m","1m|1m",3,doras=["1p"])
    for seat in range(1,threat_count+1):r["state"]["riichi"][seat]="accepted"
    action,analysis=choose(r)
    assert action["kind"]=="pon" and analysis["shanten"]==2
    assert analysis["projected_han"]==3 and analysis["target_route"]=="yakuhai"


def test_yakuhai_pon_does_not_trade_useful_draws_for_remote_honitsu():
    action,analysis=choose(call_report("55z123456m22m89p1z","5z","5z|5z"))
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["rejections"]["slower_than_post_call_plan"]>0


def test_dora_alone_still_does_not_make_an_open_yaku():
    r=call_report("11p234m567s89m2z3z4z","1p","1p|1p",doras=["9p"])
    action,analysis=choose(r)
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["rejections"]["no_reachable_open_yaku"]>0


def test_defensive_threats_do_not_change_offensive_discard_into_fold():
    r=report("123m456p789s11z99p2z")
    original,_=choose(r)
    for seat in range(1,4):r["state"]["riichi"][seat]="accepted"
    action,analysis=choose(r)
    assert action==original and analysis["mode"]=="attack_push"


def test_dominant_suit_can_target_chinitsu_without_claiming_it_is_scored_han():
    b=board("1122334455m67p1z")
    target=project_attack(b,b["self"]["hand"],known_bonus(b,b["self"]["hand"]))
    assert target["target_route"]=="chinitsu" and target["projected_han"]==7
    assert target["route_cost"]==3


def test_dead_value_honor_pair_does_not_become_a_yakuhai_target():
    b=board("55z123m456p78s22p")
    b["visible_tile_counts"]["5z"]=4
    assert project_attack(b,b["self"]["hand"])["target_route"]!="yakuhai"


def test_optional_rebuilding_can_accept_extra_shanten_when_explicitly_enabled():
    b=board("123m456p789s11z99p2z")
    settings=default_mahjong_playbooks().get(4,"atk").thresholds_for("D1")
    def option(tile,distance,han,cost):
        return {"action":{"kind":"discard","tile":tile},"shanten":distance,"effective_ukeire":8,
                "projected_han":han,"route_cost":cost,"wait_value":None,"dora_loss":0,"pair_break_loss":0}
    settings["allow_value_rebuild"]=True
    fast=option("1z",0,2,0);valuable=option("9p",1,5,1)
    assert offensive(b,[fast,valuable],settings) is valuable
    b["wall_remaining"]=10
    assert offensive(b,[fast,valuable],settings) is fast


def test_legal_offered_win_is_not_refused_for_a_more_valuable_future_hand():
    from tests.mahjong_soul.test_win_input import offer
    r,_=offer()
    assert choose(r)[0]["kind"]=="tsumo"


def test_tanyao_target_drops_terminal_dora_but_keeps_compatible_red_bonus():
    b=board("11p234s678s55m",melds=[{"type":0,"tiles":["4m","0m","6m"]}],doras=["9p"])
    bonus=known_bonus(b,b["self"]["hand"])
    assert bonus==3
    target=next(t for t in project_attack(b,b["self"]["hand"],bonus,all_targets=True) if t["target_route"]=="tanyao")
    assert target["projected_han"]==2


def test_chi_does_not_sacrifice_most_draws_for_speculative_honitsu():
    action,analysis=choose(call_report("23m456789m55z12p9s","1m","2m|3m",2))
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["rejections"]["slower_than_post_call_plan"]>0


def test_recorded_east_four_pon_does_not_trade_closed_sequences_for_remote_toitoi():
    # Self was South. North is not Yakuhai; both Pon offers lose the closed
    # Riichi route despite generic Shanten advertising quick sequence progress.
    r=call_report("11234m1235s44z","7p","7p|7p")
    r["state"]["hand"] += ["7p","7p"]
    r["state"]["visible_tile_counts"]["7p"]=3
    action,analysis=choose(r)
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["accepted"] is False


def test_toitoi_progress_excludes_sequence_extensions_and_counts_triplet_draws():
    from agents.mahjong_soul.attack_routes import toitoi_progress
    b=board("123s11m4p5s",melds=[{"type":1,"tiles":["7p"]*3},{"type":1,"tiles":["4z"]*3}])
    distance,improving=toitoi_progress(b,b["self"]["hand"])
    assert distance==3
    assert "4s" not in {t["tile"] for t in improving}
    assert "1m" in {t["tile"] for t in improving}


def test_toitoi_ready_and_complete_shapes_have_exact_distance():
    from agents.mahjong_soul.attack_routes import toitoi_progress
    b=board("111m22p33s",melds=[{"type":1,"tiles":["7p"]*3},{"type":1,"tiles":["4z"]*3}])
    distance,improving=toitoi_progress(b,b["self"]["hand"])
    assert distance==0
    assert {t["tile"] for t in improving}=={"2p","3s"}
    assert toitoi_progress(b,b["self"]["hand"]+["2p"])[0]==-1
