from copy import deepcopy
from agents.mahjong_soul.playbook_policy import PlaybookPolicy
from agents.mahjong_soul.attack_policy import offensive,enrich
from agents.mahjong_soul.attack_value import yaku_routes,scored_han
from agents.mahjong_soul.attack_routes import project_attack
from games.mahjong_soul.live.runtime.decision import decision_request
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from tests.mahjong_soul.test_attack_v2 import report,board
from tests.mahjong_soul.test_efficiency import tiles


def test_real_policy_retains_plan_and_resets_for_new_round_and_connection():
    policy=PlaybookPolicy(style="atk");r=report("123456789m11z22p3s")
    policy.choose(decision_request(r));first=policy.last_analysis["hand_plan"]
    assert first["transition"]=="start" and first["current"]
    r["state"]["round"]["liqibang"]=1
    policy.choose(decision_request(r));assert policy.last_analysis["hand_plan"]["transition"]=="retain"
    r["state"]["round"]["ben"]=1
    policy.choose(decision_request(r));assert policy.last_analysis["hand_plan"]["previous"] is None
    r["game_connection"]="another-match"
    policy.choose(decision_request(r));assert policy.last_analysis["hand_plan"]["previous"] is None


def test_plan_preference_avoids_small_switch_but_allows_large_value_gain():
    b=board("123m456p789s11z99p2z");settings=default_mahjong_playbooks().get(4,"atk").thresholds_for("D1")
    def option(tile,route,han):
        return {"action":{"kind":"discard","tile":tile},"target_route":route,"target_suit":"m",
                "shanten":1,"effective_ukeire":8,"projected_han":han,"route_cost":1,
                "wait_value":None,"dora_loss":0,"pair_break_loss":0}
    old=option("1z","honitsu",4);new=option("2z","chinitsu",4.1)
    settings["preferred_plan"]=("honitsu","m")
    assert offensive(b,[old,new],settings) is old
    new["projected_han"]=6
    assert offensive(b,[old,new],settings) is new


def test_proven_exposed_sequence_yaku_are_recognized_without_loose_tile_guessing():
    for name,groups in (("sanshoku",["123m","123p","123s"]),("ittsu",["123m","456m","789m"])):
        b=board("789p1z",melds=[{"type":0,"tiles":tiles(g)} for g in groups])
        assert yaku_routes(b,b["self"]["hand"])["routes"][name]==1
        assert any(t["target_route"]==name for t in project_attack(b,b["self"]["hand"],all_targets=True))
    b=board("123m123p123s12z34p")
    assert "sanshoku" not in yaku_routes(b,b["self"]["hand"])["routes"]


def test_actual_wait_scoring_replaces_remote_target_han_at_tenpai():
    from agents.mahjong_soul.efficiency import rank_discards
    r=report("123m123p123s111z23s",doras=["1s","1s"])
    q=decision_request(r)
    options=enrich(q["observation"]["board"],rank_discards(q))
    ready=[o for o in options if o["wait_value"]]
    assert ready
    for o in ready:assert o["projected_han"]==scored_han(o["wait_value"],o["riichi_offered"])
