from agents.mahjong_soul.assist_preferences import assist_preferences


def request(riichi="none"):
    return {"observation":{"board":{"self_seat":0,"players":[{"seat":0,"riichi":riichi}]}}}


def test_open_tenpai_does_not_lock_future_draws():
    p=assist_preferences(request(),{"kind":"discard"},{"shanten":0,"target_route":"honitsu"})
    assert not p["auto_discard"] and not p["skip_calls"] and p["auto_win"]
    assert not p["auto_kita"]


def test_closed_preference_reopens_on_route_change():
    a={"shanten":1,"hand_plan":{"current":["riichi",None]}}
    assert assist_preferences(request(),{"kind":"discard"},a)["skip_calls"]
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


def test_closed_yakuman_routes_keep_call_skip_preference():
    for route in ("yakuman_kokushi","yakuman_nine_gates"):
        assert assist_preferences(request(),{"kind":"discard"},{"shanten":1,"target_route":route})["skip_calls"]
