import pytest
from games.mahjong_soul.live.runtime.win import plan_win
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_input import inputs, Mouse
from tests.mahjong_soul.test_calls import chi_offer


def offer():
    report, _ = inputs(); report["state"]["drawn_tile"] = "0p"
    report["state"]["operations"]["operation_list"].append({"type": 8})
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "stage": "call_offer", "operation_types": [1, 8], "tsumo": [0.53, 0.77]}
    return report, profile


def hule(**winner):
    return {"name": "ActionHule", "step": 1, "source": "live",
            "data": {"hules": [{"seat": 0, "zimo": True, "hu_tile": "0p", **winner}]}}


def test_tsumo_confirms_exact_own_win_and_blocks_duplicates():
    report, profile = offer(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_win(report, profile, now=10)
    controller.submit(plan, report, enabled=True, now=11)
    assert not controller.observe("other", hule(), now=12)
    restored = hule(); restored["source"] = "restore"
    assert not controller.observe("game", restored, now=12)
    assert controller.observe("game", hule(), now=12)
    assert controller.snapshot()["status"] == "idle"
    with pytest.raises(ValueError): controller.submit(plan, report, enabled=True, now=11)
    assert len(mouse.clicks) == 1


@pytest.mark.parametrize("winner", [{"seat": 1}, {"zimo": False}, {"hu_tile": "5p"}])
def test_other_winner_wrong_win_type_or_red_identity_does_not_confirm(winner):
    report, profile = offer(); controller = InputController(Mouse())
    controller.submit(plan_win(report, profile, now=10), report, enabled=True, now=11)
    assert not controller.observe("game", hule(**winner), now=12)
    report["state_ready"] = False
    assert controller.update(report, now=12)["status"] == "blocked"


@pytest.mark.parametrize("bad", ["no_offer", "no_draw", "wrong_layout"])
def test_invalid_win_context_is_rejected(bad):
    report, profile = offer()
    if bad == "no_offer": report["state"]["operations"] = None
    if bad == "no_draw": report["state"]["drawn_tile"] = None
    if bad == "wrong_layout": profile["operation_types"] = [8]
    with pytest.raises(ValueError): plan_win(report, profile, now=10)


def test_ron_offline_path_requires_current_discard_and_can_match_multiple_winners():
    report, _ = chi_offer()
    report["state"]["operations"] = {"seat": 0, "operation_list": [{"type": 9}]}
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "stage": "call_offer", "operation_types": [9], "ron": [0.53, 0.77]}
    plan = plan_win(report, profile, "ron", now=10)
    controller = InputController(Mouse()); controller.submit(plan, report, enabled=True, now=11)
    event = hule(zimo=False, hu_tile="7p")
    event["data"]["hules"].insert(0, {"seat": 1, "zimo": False, "hu_tile": "7p"})
    assert controller.observe("game", event, now=12)
    report["state"]["discards"][3][0]["called"] = None
    with pytest.raises(ValueError): plan_win(report, profile, "ron", now=10)
