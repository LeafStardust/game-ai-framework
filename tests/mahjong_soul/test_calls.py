import pytest
from games.mahjong_soul.live.runtime.calls import plan_pon, PonExecutor
from tests.mahjong_soul.test_input import inputs, Mouse


def offer():
    report, _ = inputs()
    report["state"]["hand"] = ["0p", "5p"]
    report["last_event"] = {"name": "ActionDiscardTile", "step": 0}
    report["state"]["turn"] = 3
    report["state"]["discards"][3] = [{"tile": "5p", "called": False}]
    report["state"]["operations"] = {"seat": 0, "operation_list": [{"type": 3, "combination": ["0p|5p"]}]}
    return report, {"version": 1, "verified": True, "client_size": [925, 520],
                    "operation_types": [3], "pon": [0.53, 0.77]}


def test_single_choice_pon_click_and_exact_meld_confirmation():
    report, profile = offer()
    plan = plan_pon(report, profile, now=10)
    mouse = Mouse()
    executor = PonExecutor(mouse)
    executor.execute(plan, report, enabled=True, now=11)
    event = {"name": "ActionChiPengGang", "step": 1, "source": "live",
             "data": {"seat": 0, "type": 1, "tiles": ["0p", "5p", "5p"], "froms": [0, 0, 3]}}
    assert not executor.observe("other", event)
    assert not executor.observe("game", dict(event, source="restore"))
    assert executor.observe("game", event)
    with pytest.raises(ValueError): executor.execute(plan, report, enabled=True, now=11)
    assert len(mouse.clicks) == 1


def test_ambiguous_red_five_choices_and_changed_button_layout_are_rejected():
    report, profile = offer()
    profile["operation_types"] = [2, 3]
    with pytest.raises(ValueError): plan_pon(report, profile, now=10)
    profile["operation_types"] = [3]
    report["state"]["operations"]["operation_list"][0]["combination"].append("5p|5p")
    with pytest.raises(ValueError, match="choice panel"): plan_pon(report, profile, now=10)


def test_expired_and_changed_pon_plans_do_not_click():
    report, profile = offer()
    plan = plan_pon(report, profile, now=10)
    mouse = Mouse(); executor = PonExecutor(mouse)
    with pytest.raises(ValueError, match="expired"): executor.execute(plan, report, enabled=True, now=12)
    report["state"]["step"] += 1
    with pytest.raises(ValueError, match="changed"): executor.execute(plan, report, enabled=True, now=11)
    assert not mouse.clicks


def chi_offer():
    report, _ = inputs()
    report["last_event"] = {"name": "ActionDiscardTile", "step": 0}
    state = report["state"]
    state["hand"] = ["0p", "6p"]
    state["turn"] = 3
    state["discards"][3] = [{"tile": "7p", "called": False}]
    state["operations"] = {"seat": 0, "operation_list": [{"type": 2, "combination": ["0p|6p"]}]}
    return report, {"version": 1, "verified": True, "client_size": [925, 520],
                    "operation_types": [2], "chi": [0.53, 0.77]}


def test_chi_confirmation_preserves_red_five_and_source_identity():
    from games.mahjong_soul.live.runtime.calls import plan_chi, ChiExecutor
    report, profile = chi_offer()
    executor = ChiExecutor(Mouse())
    executor.execute(plan_chi(report, profile, now=10), report, enabled=True, now=11)
    event = {"name": "ActionChiPengGang", "step": 1, "source": "live",
             "data": {"seat": 0, "tiles": ["7p", "0p", "6p"], "froms": [3, 0, 0]}}
    assert not executor.observe("game", dict(event, source="restore"))
    assert not executor.observe("game", dict(event, data=dict(event["data"], tiles=["7p", "5p", "6p"])))
    assert not executor.observe("game", dict(event, data=dict(event["data"], froms=[0, 3, 0])))
    assert executor.observe("game", event)


@pytest.mark.parametrize("problem", ["multiple", "wrong_source", "not_sequence", "unknown_discard"])
def test_chi_rejects_ambiguous_or_inconsistent_offer(problem):
    from games.mahjong_soul.live.runtime.calls import plan_chi
    report, profile = chi_offer()
    state = report["state"]
    if problem == "multiple": state["operations"]["operation_list"][0]["combination"].append("6p|8p")
    if problem == "wrong_source": state["turn"] = 2
    if problem == "not_sequence": state["discards"][3][0]["tile"] = "9p"
    if problem == "unknown_discard": state["discards"][3][0]["called"] = None
    with pytest.raises(ValueError): plan_chi(report, profile, now=10)


def multi_chi_offer():
    report, _ = chi_offer()
    state = report["state"]
    state["hand"] = ["2m", "4m", "0m", "5m"]
    state["discards"][3][0]["tile"] = "3m"
    combinations = ["2m|4m", "4m|0m", "4m|5m"]
    state["operations"]["operation_list"][0]["combination"] = combinations
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "operation_types": [2], "stage": "chi_choices", "combinations": list(combinations),
               "choice_points": [[0.38, 0.72], [0.49, 0.72], [0.60, 0.72]]}
    return report, profile, combinations


def test_multi_chi_chooses_exact_red_combination_and_coordinate():
    from games.mahjong_soul.live.runtime.calls import plan_chi, ChiExecutor
    report, profile, combinations = multi_chi_offer()
    plan = plan_chi(report, profile, combination="4m|0m", visible_combinations=list(combinations), now=10)
    assert plan.tiles == ("4m", "0m", "3m")
    mouse = Mouse(); executor = ChiExecutor(mouse)
    executor.execute(plan, report, enabled=True, now=11)
    assert mouse.clicks == [(0.49, 0.72, 925, 520)]
    event = {"name": "ActionChiPengGang", "step": 1, "source": "live",
             "data": {"seat": 0, "tiles": ["4m", "5m", "3m"], "froms": [0, 0, 3]}}
    assert not executor.observe("game", event)
    event["data"]["tiles"][1] = "0m"
    assert executor.observe("game", event)


@pytest.mark.parametrize("problem", ["unobserved", "reordered", "profile_order", "missing_point", "unknown_choice"])
def test_multi_chi_rejects_unverified_or_changed_panel(problem):
    from games.mahjong_soul.live.runtime.calls import plan_chi
    report, profile, combinations = multi_chi_offer()
    visible, choice = list(combinations), "4m|0m"
    if problem == "unobserved": visible = None
    if problem == "reordered": visible.reverse()
    if problem == "profile_order": profile["combinations"].reverse()
    if problem == "missing_point": profile["choice_points"].pop()
    if problem == "unknown_choice": choice = "5m|6m"
    with pytest.raises(ValueError):
        plan_chi(report, profile, combination=choice, visible_combinations=visible, now=10)


def test_pon_rejects_wrong_red_contribution_and_source():
    report, profile = offer(); executor = PonExecutor(Mouse())
    executor.execute(plan_pon(report, profile, now=10), report, enabled=True, now=11)
    event = {"name": "ActionChiPengGang", "step": 1, "source": "live",
             "data": {"seat": 0, "type": 1, "tiles": ["5p", "5p", "5p"], "froms": [0, 0, 3]}}
    assert not executor.observe("game", event)
    event["data"]["tiles"][0] = "0p"
    event["data"]["froms"] = [3, 0, 0]
    assert not executor.observe("game", event)
    event["data"]["froms"] = [0, 0, 3]
    assert executor.observe("game", event)


@pytest.mark.parametrize("problem", ["own_discard", "unknown_source", "called", "wrong_kind"])
def test_pon_rejects_uncertain_source_discard(problem):
    report, profile = offer(); state = report["state"]
    if problem == "own_discard": state["turn"] = 0
    if problem == "unknown_source": state["turn"] = None
    if problem == "called": state["discards"][3][0]["called"] = None
    if problem == "wrong_kind": state["discards"][3][0]["tile"] = "6p"
    with pytest.raises(ValueError): plan_pon(report, profile, now=10)


def combined_offer():
    report, _ = chi_offer()
    state = report["state"]
    state["hand"] = ["7s", "8s", "9s", "9s"]
    state["discards"][3][0]["tile"] = "9s"
    state["operations"]["operation_list"] = [
        {"type": 2, "combination": ["7s|8s"]},
        {"type": 3, "combination": ["9s|9s"]}]
    profile = {"version": 1, "verified": True, "stage": "call_offer",
               "client_size": [925, 520], "operation_types": [2, 3],
               "chi": [(354-1)/924, (433-31)/519],
               "pon": [(493-1)/924, (433-31)/519],
               "skip": [(626-1)/924, (433-31)/519]}
    return report, profile


def test_combined_offer_uses_distinct_chi_pon_and_skip_points():
    from games.mahjong_soul.live.runtime.calls import plan_chi
    from games.mahjong_soul.live.runtime.skip import plan_skip
    report, profile = combined_offer()
    chi = plan_chi(report, profile, now=10)
    pon = plan_pon(report, profile, now=10)
    skip = plan_skip(report, profile, now=10)
    assert chi.x < pon.x < skip.x
    assert chi.tiles == ("7s", "8s", "9s")
    assert pon.tiles == ("9s", "9s", "9s")


@pytest.mark.parametrize("single_type", [2, 3])
def test_single_button_calibration_cannot_be_reused_for_combined_offer(single_type):
    from games.mahjong_soul.live.runtime.calls import plan_chi
    report, profile = combined_offer()
    profile["operation_types"] = [single_type]
    for planner in (plan_chi, plan_pon):
        with pytest.raises(ValueError, match="layout"): planner(report, profile, now=10)


def test_combined_call_choice_is_serialized_and_chi_confirmation_is_exact():
    from games.mahjong_soul.live.runtime.calls import plan_chi
    from games.mahjong_soul.live.runtime.controller import InputController
    report, profile = combined_offer(); mouse = Mouse(); controller = InputController(mouse)
    controller.submit(plan_chi(report, profile, now=10), report, enabled=True, now=11)
    with pytest.raises(ValueError, match="overlapping"):
        controller.submit(plan_pon(report, profile, now=10), report, enabled=True, now=11)
    assert controller.observe("game", {"name": "ActionChiPengGang", "step": 1, "source": "live",
                              "data": {"seat": 0, "tiles": ["7s", "8s", "9s"], "froms": [0, 0, 3]}}, now=12)
    assert mouse.clicks == [(*profile["chi"], 925, 520)]
