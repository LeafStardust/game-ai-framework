from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul.speed_lookahead import next_wait_quality
from agents.mahjong_soul.attack_policy import offensive
from games.mahjong_soul.playbook.sanma.east_speed import three_player_east_speed_playbook


def fixture():
    return json.loads((Path(__file__).parent/"fixtures/wait_quality_tie.json").read_text())


def test_recorded_same_speed_tie_has_different_future_waits_without_mutation():
    data=fixture();board=data["board"];before=deepcopy(board)
    assert [o["ukeire"] for o in data["options"]]==[23,23]
    values=[next_wait_quality(board,o) for o in data["options"]]
    assert values==pytest.approx(data["qualities"])
    assert values[1]>values[0] and board==before


def test_future_wait_quality_cannot_sacrifice_immediate_speed(monkeypatch):
    data=fixture();board=data["board"];settings=three_player_east_speed_playbook().thresholds_for("D1")
    settings["next_wait_tiebreak"]=True
    options=[]
    for o in data["options"]:
        options.append(dict(o,effective_ukeire=o["ukeire"],projected_han=1,route_cost=0,wait_value=None,danger=0,total_danger=0))
    assert offensive(board,options,settings)["action"]["tile"]=="7p"
    options[0]["effective_ukeire"]=24
    assert offensive(board,options,settings)["action"]["tile"]=="7s"
    options[0]["shanten"]=0;options[0]["effective_ukeire"]=1
    assert offensive(board,options,settings)["action"]["tile"]=="7s"


def test_open_and_accepted_riichi_hands_do_not_use_closed_lookahead():
    data=fixture();board=data["board"];own=next(p for p in board["players"] if p["is_self"])
    own["riichi"]="accepted"
    assert next_wait_quality(board,data["options"][0])==0
    own["riichi"]="none";own["melds"]=[{"type":1,"tiles":["5z"]*3}]
    assert next_wait_quality(board,data["options"][0])==0


def test_two_draw_candidate_is_bounded_and_preserves_shanten(monkeypatch):
    data=fixture();board=data["board"];settings=three_player_east_speed_playbook().thresholds_for("D1")
    settings["two_draw_progress"]=True
    options=[dict(o,effective_ukeire=o["ukeire"],projected_han=1,route_cost=0,wait_value=None,danger=0,total_danger=0) for o in data["options"]]
    monkeypatch.setattr("agents.mahjong_soul.speed_lookahead.next_wait_quality",lambda b,o:1 if o["action"]["tile"]=="7s" else 10)
    options[1]["effective_ukeire"]=22
    assert offensive(board,options,settings)["action"]["tile"]=="7p"
    options[1]["effective_ukeire"]=20
    assert offensive(board,options,settings)["action"]["tile"]=="7s"
    options[0]["shanten"]=0;options[0]["effective_ukeire"]=1
    assert offensive(board,options,settings)["action"]["tile"]=="7s"
