from agents.mahjong_soul.attack_policy import credible_han,offensive
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from tests.mahjong_soul.test_attack_v2 import board


def option(tile,han,cost,ukeire):
    return {"action":{"kind":"discard","tile":tile},"shanten":2,
            "effective_ukeire":ukeire,"projected_han":han,"route_cost":cost,
            "wait_value":None,"dora_loss":0,"pair_break_loss":0}


def test_south_prefers_reachable_value_over_remote_extra_han():
    b=board("123m456p789s11z99p2z")
    settings=default_mahjong_playbooks().get(4,"atk","south").thresholds_for("D1")
    settings["attack_completion"]=False
    secured=option("2z",3,0,20)
    remote=option("9p",4,4,16)
    assert offensive(b,[secured,remote],settings) is secured
    # Equally reachable high value still takes priority; no defense introduced.
    remote["route_cost"]=0
    assert offensive(b,[secured,remote],settings) is remote


def test_scored_tenpai_and_east_value_are_not_discounted():
    settings=default_mahjong_playbooks().get(3,"atk","south").thresholds_for("D1")
    o=option("2z",5,3,12)
    assert credible_han(o,settings)<5
    o["wait_value"]={"scored":True}
    assert credible_han(o,settings)==5
    assert credible_han(option("2z",5,3,12),{})==5
