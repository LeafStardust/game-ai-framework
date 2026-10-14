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
