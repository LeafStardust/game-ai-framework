from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul.discard_completion import choose_attack_completion_discard
from tests.mahjong_soul.test_discard_completion import position


def pair():
    board,options,_,_=position()
    ready=[o for o in options if o["shanten"]==2]
    base=deepcopy(ready[0]);other=deepcopy(next(o for o in ready if o["action"]!=base["action"]))
    for o in (base,other):
        o.update(projected_han=3,target_route="honitsu",route_cost=0,dora_loss=0,pair_break_loss=0)
        o.pop("target_suit",None);o.pop("yakuman_suit",None)
    key=lambda o:(int(o["action"]==base["action"]),)
    return board,base,other,key


def test_value_qualified_alternative_can_win_by_completion_without_mutating_board():
    board,base,other,key=pair();before=deepcopy(board);calls=[]
    def estimate(after,**kwargs):
        calls.append(kwargs)
        return {"available":True,"capped_draw_cost":9 if after["self"]["hand"].count(other["action"]["tile"])<board["self"]["hand"].count(other["action"]["tile"]) else 11}
    chosen=choose_attack_completion_discard(board,[base,other],key,estimator=estimate)
    assert chosen is other and chosen["completion_objective"]=="attack_value_preserving"
    assert all(c["minimum_han"]==3 and c["max_states"]==2000 for c in calls)
    assert board==before


@pytest.mark.parametrize("field,bad",[("projected_han",2),("route_cost",1),("dora_loss",1),("pair_break_loss",1)])
def test_faster_cheap_or_damaged_route_cannot_enter_forecast(field,bad):
    board,base,other,key=pair();other[field]=bad
    def fail(*a,**kw):raise AssertionError("Unqualified route forecast")
    assert choose_attack_completion_discard(board,[base,other],key,estimator=fail) is base


def test_yakuman_qualification_model_is_not_overridden():
    board,base,other,key=pair();base["target_route"]="yakuman_kokushi"
    def fail(*a,**kw):raise AssertionError("Yakuman forecast")
    assert choose_attack_completion_discard(board,[base,other],key,estimator=fail) is base


def test_yonma_uses_four_player_draw_budget_and_budget_failure_keeps_baseline():
    board,base,other,key=pair();board["player_count"]=4;board["wall_remaining"]=32;calls=[]
    def unavailable(after,**kwargs):
        calls.append(kwargs)
        return {"available":False,"reason":"state_budget"}
    assert choose_attack_completion_discard(board,[base,other],key,estimator=unavailable) is base
    assert len(calls)==2 and all(c["horizon"]==8 for c in calls)


def test_scored_value_floor_rejects_cheap_legal_tsumo():
    from tests.mahjong_soul.test_completion_speed import ready_board
    from agents.mahjong_soul.completion_speed import estimate_tsumo_draws
    board=ready_board(True);board["dora_indicators"]=[]
    low=estimate_tsumo_draws(board,horizon=6,minimum_han=1)
    high=estimate_tsumo_draws(board,horizon=6,minimum_han=13)
    assert low["completion_probability"]>0
    assert high["completion_probability"]==0 and high["capped_draw_cost"]==6


def test_live_policy_runs_south_objective_on_recorded_sanma_board():
    from agents.mahjong_soul.policy import make_policy
    f=json.loads((Path(__file__).parent/"fixtures/discard_completion_native.json").read_text())
    request=f["request"];request["observation"]["board"]["lobby"].update(match_length="south",label="3 Player South Wind")
    before=deepcopy(request);policy=make_policy("playbook","atk")
    action=policy.choose(request)
    assert action in request["actions"]
    assert policy.last_analysis["playbook_version"]=="0.4"
    assert policy.last_analysis["completion_objective"]=="attack_value_preserving"
    assert request==before


def test_south_enables_and_east_explicitly_disables_attack_completion():
    from games.mahjong_soul.playbook.model import default_mahjong_playbooks
    registry=default_mahjong_playbooks()
    for count in (3,4):
        assert registry.get(count,"atk","south").thresholds_for("D1")["attack_completion"]
        assert registry.get(count,"atk","east").thresholds_for("D1")["attack_completion"] is False


def test_equal_value_alternative_route_can_compete_on_scored_completion():
    board,base,other,key=pair();other["target_route"]="tanyao"
    def estimate(after,**kwargs):
        assert kwargs["minimum_han"]==3
        return {"available":True,"capped_draw_cost":9 if after["self"]["hand"].count(other["action"]["tile"])<board["self"]["hand"].count(other["action"]["tile"]) else 11}
    assert choose_attack_completion_discard(board,[base,other],key,estimator=estimate) is other
