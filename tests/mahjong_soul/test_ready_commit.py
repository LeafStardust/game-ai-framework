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
