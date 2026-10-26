from copy import deepcopy
from agents.mahjong_soul.assist_lock import ready_lock,improves,_check
from agents.mahjong_soul.assist_preferences import assist_preferences
from tests.mahjong_soul.test_attack_v2 import board
from tests.mahjong_soul.test_efficiency import tiles


def open_ready():
    return board("5p",melds=[{"type":0,"tiles":tiles(s)} for s in ("123p","123p","456p","789p")],doras=["4p"])


def test_open_ready_no_better_calls_or_draws_enables_both_without_riichi():
    b=open_ready();before=deepcopy(b)
    result=ready_lock(b,{"kind":"discard"})
    assert result["auto_discard"] and result["skip_calls"] and b==before
    prefs=assist_preferences({"observation":{"board":b}},{"kind":"discard"},{})
    assert prefs["auto_discard"] and prefs["skip_calls"]


def test_closed_ready_special_hand_skips_calls_without_forcing_draw_discards():
    b=board("112233445566p7z")
    result=ready_lock(b,{"kind":"discard"})
    assert result["skip_calls"] and not result["auto_discard"]


def test_threats_unready_hand_and_chosen_call_keep_options_open():
    b=open_ready();b["lobby"]["match_length"]="east";next(p for p in b["players"] if not p["is_self"])["riichi"]="accepted"
    assert not ready_lock(b,{"kind":"discard"})
    assert not ready_lock(board("123m456p789s125z9p"),{"kind":"discard"})
    assert not ready_lock(open_ready(),{"kind":"pon"})


def test_cannot_enable_auto_discard_before_a_different_selected_tile_is_discarded():
    b=open_ready();b["self"]["hand"].append("1z");b["self"]["drawn_tile"]="5p"
    prefs=assist_preferences({"observation":{"board":b}},{"kind":"discard","tile":"1z"},{})
    assert prefs["skip_calls"] and not prefs["auto_discard"]


def test_value_and_speed_comparisons_differ_without_accepting_furiten():
    base={"dama_points":8000,"dama_ukeire":2,"tsumo_points":8000,"tsumo_ukeire":2}
    cheap={"dama_points":2000,"dama_ukeire":3,"tsumo_points":2000,"tsumo_ukeire":3,"ron_blocked":False}
    assert not improves(cheap,base) and improves(cheap,base,True)
    cheap["ron_blocked"]=True
    assert not improves(cheap,base,True)


def test_pair_route_evidence_does_not_hide_all_triplets():
    from agents.mahjong_soul.attack_policy import enrich
    from agents.mahjong_soul.efficiency import rank_discards
    b=board("112233445566p7z1z")
    req={"observation":{"board":b},"actions":[{"kind":"discard","tile":t} for t in set(b["self"]["hand"])]}
    options=enrich(b,rank_discards(req))
    assert any({x["route"] for x in o["pair_route_comparison"]}=={"chiitoitsu","toitoi"} for o in options)


def test_incomplete_lock_check_does_not_enable_assists(monkeypatch):
    from types import SimpleNamespace
    from agents.mahjong_soul import assist_lock
    _check.cache_clear();ticks=iter([0,1])
    monkeypatch.setattr(assist_lock,"committed_ready",lambda *a:False)
    monkeypatch.setattr(assist_lock,"time",SimpleNamespace(perf_counter=lambda:next(ticks)))
    assert not ready_lock(open_ready(),{"kind":"discard"})
    _check.cache_clear()


def test_all_triplets_is_selected_when_it_is_closer_and_more_valuable():
    from tests.mahjong_soul.test_attack_v2 import report,choose
    action,analysis=choose(report("111m222p333s55z66z1z"))
    assert action=={"kind":"discard","tile":"1z"} and analysis["target_route"]=="toitoi"
    routes={r["route"]:r for r in analysis["pair_route_comparison"]}
    assert routes["toitoi"]["shanten"]==0 and routes["chiitoitsu"]["shanten"]==3


def test_reached_value_goal_commits_instead_of_waiting_for_optional_upgrades():
    b=board("8p",melds=[{"type":0,"tiles":tiles(s)} for s in ("123p","123p","456p","456p")])
    result=ready_lock(b,{"kind":"discard"})
    assert result["skip_calls"] and result["auto_discard"]
    assert result["reason"]=="committed_open_tenpai"


def test_existing_closed_kan_option_is_not_suppressed():
    b=board("2222p345p678s55p3p")
    result=ready_lock(b,{"kind":"discard"})
    assert not result.get("skip_calls") and not result.get("auto_discard")
