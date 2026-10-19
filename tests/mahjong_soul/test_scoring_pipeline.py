from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.state import GameState
from games.mahjong_soul.live.runtime.decision import offered_actions
from games.mahjong_soul.live.runtime.win import plan_win
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from agents.mahjong_soul.scoring import score_offered_win,nagashi_eligible
from tests.mahjong_soul.test_efficiency import tiles


def report(state,name):
    return {"state":state.snapshot(),"state_ready":True,"connection_open":True,"game_connection":"test",
            "last_event":{"name":name,"step":state.last_step}}


def test_dealer_initial_hand_can_offer_and_score_tenhou():
    state=GameState(0)
    state.apply({"name":"ActionNewRound","step":0,"data":{"ju":0,"tiles":tiles("123456m789p234s55p"),
                 "scores":[25000]*4,"operation":{"seat":0,"operation_list":[{"type":8}]}}})
    r=report(state,"ActionNewRound");action=offered_actions(r)[0]
    value=score_offered_win(observation_from_snapshot(r)["board"],action)
    assert value["legal"] and "tenhou" in {y["key"] for y in value["yaku_details"]}


def test_robbed_kan_offer_uses_verified_kan_tile_and_scores_chankan():
    state=GameState(0)
    state.apply({"name":"ActionNewRound","step":0,"data":{"tiles":tiles("123456m789p23s55p"),"scores":[25000]*4}})
    state.melds[1]=[{"type":1,"tiles":tiles("444s")}]
    state.apply({"name":"ActionAnGangAddGang","step":1,"data":{"seat":1,"type":2,"tiles":"4s",
                 "operation":{"seat":0,"operation_list":[{"type":9}]}}})
    r=report(state,"ActionAnGangAddGang");action=next(a for a in offered_actions(r) if a["kind"]=="ron")
    assert action["tile"]=="4s" and action["source_seat"]==1
    profile={"version":1,"verified":True,"stage":"call_offer","operation_types":[9],"client_size":[1920,1080],"ron":[.5,.7]}
    assert plan_win(r,profile,"ron",now=1).tile=="4s"
    value=score_offered_win(observation_from_snapshot(r)["board"],action)
    assert value["legal"] and "chankan" in {y["key"] for y in value["yaku_details"]}
    missing=deepcopy(r);missing["state"]["win_source"]=None
    with pytest.raises(ValueError):offered_actions(missing)


def test_nagashi_requires_uncalled_terminal_honor_river_not_dora():
    state=GameState(0);state.discards[0]=[{"tile":"1m","called":False},{"tile":"7z","called":False}]
    b=observation_from_snapshot(report(state,"ActionNoTile"))["board"]
    assert nagashi_eligible(b)
    b["players"][0]["discards"][0]["called"]=True
    assert not nagashi_eligible(b)


def test_hypothetical_first_discard_riichi_has_double_value_without_inventing_ippatsu():
    from agents.mahjong_soul.attack_value import tenpai_value
    from tests.mahjong_soul.test_attack_v2 import board
    b=board("123456m789p23s55p")
    b["self"]["scoring_context"]={"double_riichi_available":True}
    profile=tenpai_value(b,b["self"]["hand"])
    for w in profile["waits"]:
        for mode,value in w["values"].items():
            keys={y["key"] for y in value["yaku_details"]}
            assert "ippatsu" not in keys
            if mode=="riichi":assert "daburu_riichi" in keys and "riichi" not in keys


def test_capture_gap_invalidates_bonus_history_instead_of_inventing_first_turn_yaku():
    state=GameState(0)
    state.apply({"name":"ActionNewRound","step":0,"data":{"tiles":tiles("123456m789p23s55p"),"scores":[25000]*4}})
    state.scoring_context.ippatsu[0]=True
    state.apply({"name":"ActionDiscardTile","step":3,"data":{"seat":1,"tile":"1z"}})
    context=state.snapshot()["scoring_context"]
    assert not context["history_complete"] and not context["ippatsu"]
    assert not context["double_riichi_available"] and context["win"]=={}
