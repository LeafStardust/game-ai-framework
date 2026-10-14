import pytest
from games.mahjong_soul.live.runtime.calls import plan_pon, PonExecutor
from tests.mahjong_soul.test_input import inputs, Mouse


def offer():
    report, _ = inputs()
    report["state"]["hand"] = ["0p", "5p"]
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
             "data": {"seat": 0, "type": 1, "tiles": ["0p", "5p", "5p"]}}
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
