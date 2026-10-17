from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.decision import decision_request, validate_proposal, offered_actions
from tests.mahjong_soul.test_input import inputs
from tests.mahjong_soul.test_calls import offer as pon_offer, chi_offer
from tests.mahjong_soul.test_kan_input import offer as closed_offer, open_offer, added_offer
from tests.mahjong_soul.test_win_input import offer as win_offer


def proposal(request, action=None):
    return {"version":1,"request_id":request["request_id"],"board_token":request["board_token"],
            "action":deepcopy(request["actions"][0] if action is None else action)}


def test_discard_request_proposal_is_isolated_and_nonexecutable():
    report, _ = inputs(); original = deepcopy(report)
    request = decision_request(report, now=10)
    assert request["actions"] == [{"kind":"discard","tile":"0p"}]
    result = validate_proposal(request, proposal(request), report, now=11)
    assert result["executable"] is False
    result["action"]["tile"] = "1m"
    request["observation"]["board"]["self"]["hand"].clear()
    assert report == original and request["actions"][0]["tile"] == "0p"
    # Request candidates cannot be altered to authorize a new action.
    request["actions"].append({"kind":"discard","tile":"1m"})
    with pytest.raises(ValueError):
        validate_proposal(request, proposal(request, request["actions"][-1]), report, now=11)


@pytest.mark.parametrize("change", ["generation","connection","step","round","hand","operations","closed","incomplete"])
def test_stale_proposal_never_validates(change):
    report, _ = inputs(); request = decision_request(report, now=10)
    changed = deepcopy(report)
    if change == "generation": changed["game_generation"] += 1
    if change == "connection": changed["game_connection"] = "other"
    if change == "step": changed["state"]["step"] += 1
    if change == "round": changed["state"]["round"]["ben"] += 1
    if change == "hand": changed["state"]["hand"] = ["1m"]
    if change == "operations": changed["state"]["operations"]["operation_list"] = []
    if change == "closed": changed["connection_open"] = False
    if change == "incomplete": changed["state_ready"] = False
    with pytest.raises(ValueError): validate_proposal(request, proposal(request), changed, now=11)


@pytest.mark.parametrize("now", [9,12,float("nan"),float("inf"),True])
def test_expired_or_invalid_decision_time(now):
    report, _ = inputs(); request = decision_request(report, now=10)
    with pytest.raises(ValueError): validate_proposal(request, proposal(request), report, now=now)


@pytest.mark.parametrize("ttl", [0,-1,float("inf"),float("nan"),True])
def test_invalid_request_lifetime(ttl):
    report, _ = inputs()
    with pytest.raises(ValueError): decision_request(report, now=10, ttl=ttl)


@pytest.mark.parametrize("bad", ["id","token","version","extra","tile","coordinates"])
def test_proposals_require_exact_contract(bad):
    report, _ = inputs(); request = decision_request(report, now=10); value = proposal(request)
    if bad == "id": value["request_id"] = "other"
    if bad == "token": value["board_token"] = "other"
    if bad == "version": value["version"] = True
    if bad == "extra": value["execute"] = True
    if bad == "tile": value["action"]["tile"] = "5p"
    if bad == "coordinates": value["action"]["x"] = .5
    with pytest.raises(ValueError): validate_proposal(request, value, report, now=11)


@pytest.mark.parametrize("fixture,kind", [(pon_offer,"pon"),(chi_offer,"chi"),(closed_offer,"closed_kan"),
                                           (open_offer,"open_kan"),(added_offer,"added_kan"),(win_offer,"tsumo")])
def test_supported_server_intents_preserve_exact_tiles(fixture, kind):
    report, _ = fixture(); request = decision_request(report, now=10)
    action = next(a for a in request["actions"] if a["kind"] == kind)
    assert validate_proposal(request, proposal(request, action), report, now=11)["action"] == action
    assert ("skip" in [a["kind"] for a in request["actions"]]) == (kind in ["pon","chi","open_kan"])


def test_multiple_red_five_pon_choices_are_distinct_intents_not_click_positions():
    report, _ = pon_offer(); report["state"]["hand"] += ["5p"]
    report["state"]["operations"]["operation_list"][0]["combination"].append("5p|5p")
    actions = offered_actions(report)
    assert [a["combination"] for a in actions if a["kind"] == "pon"] == ["0p|5p","5p|5p"]
    assert all("x" not in a and "slot" not in a for a in actions)


def test_riichi_order_and_red_equivalent_discard_restrictions():
    report, _ = inputs(); state = report["state"]
    state["hand"] = ["0p","5p","1m"]
    state["operations"]["operation_list"] = [{"type":7,"combination":["1m","1m"]},
                                                {"type":1,"combination":["5p"]}]
    assert offered_actions(report) == [{"kind":"riichi","tile":"1m"},{"kind":"discard","tile":"1m"}]
    state["operations"]["operation_list"][0]["combination"] = ["0p"]
    with pytest.raises(ValueError): offered_actions(report)


def test_ron_requires_known_uncalled_opponent_discard():
    report, _ = pon_offer(); report["state"]["operations"]["operation_list"] = [{"type":9}]
    assert offered_actions(report) == [{"kind":"ron","tile":"5p","source_seat":3},{"kind":"skip"}]
    report["state"]["discards"][3][-1]["called"] = True
    with pytest.raises(ValueError): offered_actions(report)


@pytest.mark.parametrize("bad", ["unknown","duplicate","bad_tile","missing_tile","bad_combination","wrong_seat"])
def test_malformed_or_unsupported_operations_block_request(bad):
    report, _ = pon_offer(); operation = report["state"]["operations"]
    if bad == "unknown": operation["operation_list"].append({"type":11})
    if bad == "duplicate": operation["operation_list"] *= 2
    if bad == "bad_tile": report["state"]["hand"] = ["0z"]
    if bad == "missing_tile": report["state"]["hand"] = []
    if bad == "bad_combination": operation["operation_list"][0]["combination"] = ["0p|6p"]
    if bad == "wrong_seat": operation["seat"] = 1
    with pytest.raises(ValueError): decision_request(report, now=10)
