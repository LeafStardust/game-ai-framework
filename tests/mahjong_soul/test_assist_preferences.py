from agents.mahjong_soul.assist_preferences import assist_preferences


def request(riichi="none"):
    return {"observation":{"board":{"self_seat":0,"players":[{"seat":0,"riichi":riichi}]}}}


def test_open_tenpai_does_not_lock_future_draws():
    p=assist_preferences(request(),{"kind":"discard"},{"shanten":0,"target_route":"honitsu"})
    assert not p["auto_discard"] and not p["skip_calls"] and p["auto_win"]
    assert not p["auto_kita"]


def test_provisional_closed_preference_keeps_calls_available():
    a={"shanten":1,"hand_plan":{"current":["riichi",None]}}
    assert not assist_preferences(request(),{"kind":"discard"},a)["skip_calls"]
    a["hand_plan"]["current"]=["honitsu","s"]
    assert not assist_preferences(request(),{"kind":"discard"},a)["skip_calls"]


def test_only_accepted_riichi_locks_discards():
    for state in ("none","unknown","declared"):
        assert not assist_preferences(request(state),{"kind":"discard"},{})["auto_discard"]
    p=assist_preferences(request("accepted"),{"kind":"discard"},{})
    assert p["auto_discard"] and p["skip_calls"]


def test_selected_call_keeps_prompts_available():
    p=assist_preferences(request(),{"kind":"pon"},{"shanten":0,"target_route":"riichi"})
    assert not p["skip_calls"]


def test_provisional_closed_yakuman_routes_keep_offers_available():
    for route in ("yakuman_kokushi","yakuman_nine_gates"):
        assert not assist_preferences(request(),{"kind":"discard"},{"shanten":1,"target_route":route})["skip_calls"]


def test_recorded_closed_hand_can_call_white_dragon_for_legal_tenpai():
    import json
    from pathlib import Path
    from agents.mahjong_soul.policy import make_policy
    data=json.loads((Path(__file__).parent/"fixtures/suppressed_white_dragon_pon.json").read_text())
    req=data["request"];policy=make_policy("playbook","atk")
    action=policy.choose(req)
    assert action=={"kind":"pon","called_tile":"5z","combination":"5z|5z"}
    notes=policy.last_analysis["call_evaluations"]
    assert notes[0]["accepted"] and notes[0]["baseline_shanten"]==1 and notes[0]["best_shanten"]==0
    prefs=assist_preferences(req,{"kind":"discard"},{"shanten":1,"hand_plan":{"current":["riichi",None]}})
    assert not prefs["skip_calls"]


def test_auto_kita_enabled_in_ordinary_sanma_but_not_yonma():
    r=request();b=r["observation"]["board"];b.update(player_count=3,self={"hand":["1p"]})
    assert assist_preferences(r,{"kind":"discard"},{})["auto_kita"]
    b["player_count"]=4
    assert not assist_preferences(r,{"kind":"discard"},{})["auto_kita"]


def test_auto_kita_respects_retained_north_and_yakuman():
    r=request();b=r["observation"]["board"];b.update(player_count=3,self={"hand":["4z"]})
    assert assist_preferences(r,{"kind":"extract_north"},{})["auto_kita"]
    assert not assist_preferences(r,{"kind":"discard","tile":"1p"},{})["auto_kita"]
    for route in ("yakuman_kokushi","yakuman_all_honors"):
        assert not assist_preferences(r,{"kind":"extract_north"},{"target_route":route})["auto_kita"]
    b["self"]["hand"].append("4z")
    assert not assist_preferences(r,{"kind":"discard"},{})["auto_kita"]


def test_between_turn_setup_preserves_naturally_qualified_kokushi():
    r=request();b=r["observation"]["board"]
    b.update(player_count=3,self={"hand":["1m","9m","1p","9p","1s","9s","1z","2z","3z","5z","2p","3p","4p"]})
    assert not assist_preferences(r,{"kind":"discard"},{})["auto_kita"]


def test_between_turn_singleton_north_is_not_automatically_marked_essential():
    from tests.mahjong_soul.test_sanma_south_attack import south
    from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
    r=south("19m135p246s1245z6p")
    b=observation_from_snapshot(r)["board"]
    prefs=assist_preferences({"observation":{"board":b}},{"kind":"discard"},{})
    assert prefs["auto_kita"]
