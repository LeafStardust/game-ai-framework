import pytest
from games.mahjong_soul.live.runtime.kan import plan_concealed_kan
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_input import inputs, Mouse


def offer():
    report, _ = inputs()
    report["state"]["hand"] = ["0p", "5p", "5p", "5p"]
    report["state"]["operations"] = {"seat": 0, "operation_list": [
        {"type": 1}, {"type": 4, "combination": ["0p|5p|5p|5p"]}]}
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "stage": "call_offer", "operation_types": [1, 4], "kan": [0.53, 0.77]}
    return report, profile


def event(kind=3, tile="5p", source="live"):
    return {"name": "ActionAnGangAddGang", "step": 1, "source": source,
            "data": {"seat": 0, "type": kind, "tiles": tile}}


def test_concealed_kan_preserves_contribution_and_confirms_only_matching_own_event():
    report, profile = offer(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_concealed_kan(report, profile, now=10)
    assert plan.contributed_tiles == ("0p", "5p", "5p", "5p")
    controller.submit(plan, report, enabled=True, now=11)
    assert not controller.observe("other", event(), now=12)
    assert not controller.observe("game", event(source="restore"), now=12)
    assert controller.observe("game", event(), now=12)
    assert controller.snapshot()["status"] == "idle"
    assert len(mouse.clicks) == 1
    with pytest.raises(ValueError): controller.submit(plan, report, enabled=True, now=11)


@pytest.mark.parametrize("bad", ["missing", "mixed", "multi", "wrong_type", "wrong_layout", "invalid_tile"])
def test_invalid_kan_offer_or_layout_is_rejected(bad):
    report, profile = offer(); state = report["state"]
    choice = state["operations"]["operation_list"][1]
    if bad == "missing": state["hand"].pop()
    if bad == "mixed": choice["combination"] = ["0p|5p|5p|6p"]
    if bad == "multi": choice["combination"].append("1m|1m|1m|1m")
    if bad == "wrong_type": choice["type"] = 6
    if bad == "wrong_layout": profile["operation_types"] = [4]
    if bad == "invalid_tile": choice["combination"] = ["0z|0z|0z|0z"]
    with pytest.raises(ValueError): plan_concealed_kan(report, profile, now=10)


@pytest.mark.parametrize("wrong", [event(kind=2), event(tile="6p"), event(tile="5p|5p")])
def test_wrong_own_kan_event_blocks_controller(wrong):
    report, profile = offer(); controller = InputController(Mouse())
    controller.submit(plan_concealed_kan(report, profile, now=10), report, enabled=True, now=11)
    assert not controller.observe("game", wrong, now=12)
    assert controller.snapshot()["status"] == "blocked"


def open_offer():
    from tests.mahjong_soul.test_calls import offer as pon_offer
    report, profile = pon_offer()
    report["state"]["hand"] = ["0p", "5p", "5p"]
    report["state"]["operations"]["operation_list"].append({"type": 5, "combination": ["0p|5p|5p"]})
    profile.update(stage="call_offer", operation_types=[3, 5], kan=[0.53, 0.77])
    return report, profile


def test_open_kan_confirms_exact_contributions_red_identity_and_source():
    from games.mahjong_soul.live.runtime.kan import plan_open_kan
    report, profile = open_offer(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_open_kan(report, profile, now=10)
    assert plan.tiles == ("0p", "5p", "5p", "5p")
    controller.submit(plan, report, enabled=True, now=11)
    action = {"name": "ActionChiPengGang", "step": 1, "source": "live",
              "data": {"seat": 0, "type": 2, "tiles": ["5p", "0p", "5p", "5p"], "froms": [3, 0, 0, 0]}}
    assert not controller.observe("other", action, now=12)
    restored = dict(action, source="restore")
    assert not controller.observe("game", restored, now=12)
    assert controller.observe("game", action, now=12)
    assert controller.snapshot()["status"] == "idle"
    assert len(mouse.clicks) == 1


@pytest.mark.parametrize("bad", ["missing", "own_source", "called", "wrong_kind", "wrong_layout", "multi"])
def test_open_kan_rejects_invalid_offer_or_source(bad):
    from games.mahjong_soul.live.runtime.kan import plan_open_kan
    report, profile = open_offer(); state = report["state"]
    if bad == "missing": state["hand"].pop()
    if bad == "own_source": state["turn"] = 0
    if bad == "called": state["discards"][3][0]["called"] = True
    if bad == "wrong_kind": state["discards"][3][0]["tile"] = "6p"
    if bad == "wrong_layout": profile["operation_types"] = [5]
    if bad == "multi": state["operations"]["operation_list"][1]["combination"].append("5p|5p|5p")
    with pytest.raises(ValueError): plan_open_kan(report, profile, now=10)


@pytest.mark.parametrize("bad", ["source", "red", "type"])
def test_wrong_open_kan_event_does_not_confirm(bad):
    from games.mahjong_soul.live.runtime.kan import plan_open_kan
    report, profile = open_offer(); controller = InputController(Mouse())
    controller.submit(plan_open_kan(report, profile, now=10), report, enabled=True, now=11)
    data = {"seat": 0, "type": 2, "tiles": ["0p", "5p", "5p", "5p"], "froms": [0, 0, 0, 3]}
    if bad == "source": data["froms"] = [3, 0, 0, 0]
    if bad == "red": data["tiles"][0] = "5p"
    if bad == "type": data["type"] = 1
    assert not controller.observe("game", {"name": "ActionChiPengGang", "step": 1, "source": "live", "data": data}, now=12)
    assert controller.snapshot()["status"] == "blocked"


def added_offer():
    report, _ = inputs(); state = report["state"]
    state["hand"] = ["0p"]
    state["melds"][0] = [{"type": 1, "tiles": ["5p"] * 3, "froms": [0, 0, 1]}]
    state["operations"] = {"seat": 0, "operation_list": [{"type": 1},
        {"type": 6, "combination": ["5p|5p|5p|0p"]}]}
    return report, {"version": 1, "verified": True, "client_size": [925, 520],
                    "stage": "call_offer", "operation_types": [1, 6], "kan": [0.53, 0.77]}


def test_added_kan_derives_exact_fourth_tile_from_existing_pon():
    from games.mahjong_soul.live.runtime.kan import plan_added_kan
    report, profile = added_offer(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_added_kan(report, profile, now=10)
    assert plan.added_tile == "0p"
    assert plan.pon_tiles == ("5p", "5p", "5p")
    controller.submit(plan, report, enabled=True, now=11)
    assert not controller.observe("other", event(kind=2, tile="0p"), now=12)
    assert not controller.observe("game", event(kind=2, tile="0p", source="restore"), now=12)
    assert controller.observe("game", event(kind=2, tile="0p"), now=12)
    assert len(mouse.clicks) == 1


@pytest.mark.parametrize("bad", ["no_pon", "already_kan", "missing_red", "pon_red_mismatch", "multiple", "wrong_layout"])
def test_added_kan_rejects_inconsistent_offer(bad):
    from games.mahjong_soul.live.runtime.kan import plan_added_kan
    report, profile = added_offer(); state = report["state"]
    if bad == "no_pon": state["melds"][0] = []
    if bad == "already_kan": state["melds"][0][0]["type"] = 2
    if bad == "missing_red": state["hand"] = ["5p"]
    if bad == "pon_red_mismatch":
        state["melds"][0][0]["tiles"][0] = "0p"
        state["operations"]["operation_list"][1]["combination"] = ["5p|5p|5p|5p"]
    if bad == "multiple": state["operations"]["operation_list"][1]["combination"].append("1m|1m|1m|1m")
    if bad == "wrong_layout": profile["operation_types"] = [1, 4]
    with pytest.raises(ValueError): plan_added_kan(report, profile, now=10)


def test_added_kan_wrong_red_identity_blocks_confirmation():
    from games.mahjong_soul.live.runtime.kan import plan_added_kan
    report, profile = added_offer(); controller = InputController(Mouse())
    controller.submit(plan_added_kan(report, profile, now=10), report, enabled=True, now=11)
    assert not controller.observe("game", event(kind=2, tile="5p"), now=12)
    assert controller.snapshot()["status"] == "blocked"
