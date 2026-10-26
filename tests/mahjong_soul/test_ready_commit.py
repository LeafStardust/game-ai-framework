from copy import deepcopy
from agents.mahjong_soul.assist_lock import ready_lock
from agents.mahjong_soul.assist_preferences import assist_preferences
from agents.mahjong_soul.ready_commit import committed_ready
from tests.mahjong_soul.test_attack_v2 import report,call_report,choose,board
from tests.mahjong_soul.test_assist_lock import open_ready
from tests.mahjong_soul.test_efficiency import tiles


def test_pon_secures_legal_tenpai_in_already_open_no_yaku_hand():
    r=call_report("33z66z234p168s","6z","6z|6z",3,
                  melds=[{"type":1,"tiles":tiles("333s")}])
    action,analysis=choose(r)
    assert action["kind"]=="pon" and analysis["shanten"]==0
    assert analysis["wait_value"]["dama_ukeire"]>=3


def test_open_kan_does_not_open_distant_hand_for_speculative_honor_pair():
    r=call_report("999m147p208s11z46p","9m","9m|9m|9m",5,doras=["1z"])
    assert choose(r)[0]["kind"]=="skip"


def test_valuable_open_ready_hand_commits_waits_in_policy_and_assists():
    melds=[{"type":0,"tiles":tiles(s)} for s in ("123p","123p","456p","789p")]
    r=report("5z1z",melds=melds,doras=["4p"])
    r["state"]["drawn_tile"]="1z"
    action,analysis=choose(r)
    assert action=={"kind":"discard","tile":"1z"} and analysis["mode"]=="committed_open_tenpai"
    from games.mahjong_soul.live.runtime.decision import decision_request
    request=decision_request(r)
    prefs=assist_preferences(request,action,analysis)
    assert prefs["auto_discard"] and prefs["skip_calls"]
    assert prefs["reason"]=="committed_open_tenpai"


def test_south_commit_is_consistent_with_always_push_but_east_unlocks_on_threat():
    b=open_ready();profile={"ron_blocked":False,"dama_ukeire":4,"dama_points":8000}
    next(p for p in b["players"] if not p["is_self"])["riichi"]="accepted"
    b["lobby"]["match_length"]="south"
    assert committed_ready(b,profile)
    b["lobby"]["match_length"]="east"
    assert not committed_ready(b,profile)


def test_added_kan_is_evaluated_before_committed_ready_discard():
    r=report("234s567s78s77z1s",melds=[{"type":1,"tiles":tiles("111s")}],doras=["9s"])
    r["state"].update(drawn_tile="1s",scoring_context={})
    r["state"]["operations"]["operation_list"].append({"type":6,"combination":["1s|1s|1s|1s"]})
    action,analysis=choose(r)
    assert action=={"kind":"added_kan","combination":"1s|1s|1s|1s"}
    assert analysis["mode"]=="ready_hand_kan"
    from games.mahjong_soul.live.runtime.decision import decision_request
    prefs=assist_preferences(decision_request(r),action,analysis)
    assert not prefs["auto_discard"] and not prefs["skip_calls"]


def test_ready_hand_keeps_kan_available_until_fourth_tile_is_publicly_gone():
    b=board("234s567s78s77z",melds=[{"type":1,"tiles":tiles("111s")}],doras=["9s"])
    result=ready_lock(b,{"kind":"discard"})
    assert not result["auto_discard"] and not result["skip_calls"]
    assert result["reason"]=="keep_kan_available"
    b["visible_tile_counts"]["1s"]=4
    result=ready_lock(b,{"kind":"discard"})
    assert result["auto_discard"] and result["skip_calls"]


def test_riichi_assists_keep_future_legal_concealed_kan_available():
    b=board("111p234s567s89p22z")
    next(p for p in b["players"] if p["is_self"])["riichi"]="accepted"
    request={"observation":{"board":b}}
    prefs=assist_preferences(request,{"kind":"discard"},{})
    assert not prefs["skip_calls"] and not prefs["auto_discard"]
    b["visible_tile_counts"]["1p"]=4
    prefs=assist_preferences(request,{"kind":"discard"},{})
    assert prefs["skip_calls"] and prefs["auto_discard"]


def test_riichi_discard_plus_concealed_kan_offer_is_evaluated():
    r=report("1111p234p567s789s2z")
    r["state"].update(drawn_tile="1p",scoring_context={})
    r["state"]["riichi"][0]="accepted"
    r["state"]["operations"]["operation_list"].append({"type":4,"combination":["1p|1p|1p|1p"]})
    action,analysis=choose(r)
    assert action=={"kind":"closed_kan","combination":"1p|1p|1p|1p"}
    assert any(n.get("reason")=="ready_waits_and_value_preserved" for n in analysis["kan_evaluations"])
