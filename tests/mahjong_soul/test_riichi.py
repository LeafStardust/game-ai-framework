import pytest
from games.mahjong_soul.live.runtime.riichi import plan_riichi
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_input import inputs, Mouse


def offer():
    report, profile = inputs()
    report["state"]["operations"]["operation_list"].append({"type": 7, "combination": ["0p"]})
    profile.update(operation_types=[1, 7], riichi=[0.53, 0.77])
    return report, profile


def declaration(liqi=True):
    return {"name": "ActionDiscardTile", "step": 1, "source": "live",
            "data": {"seat": 0, "tile": "0p", "is_liqi": liqi}}


def test_riichi_three_click_flow_waits_for_server_acceptance():
    report, profile = offer(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_riichi(report, profile, 0, "0p", now=10)
    controller.submit(plan, report, enabled=True, now=11)
    with pytest.raises(ValueError): controller.select_riichi_discard(plan, report, ["5p"], enabled=True, now=11)
    controller.select_riichi_discard(plan, report, ["0p"], enabled=True, now=11)
    controller.confirm_selection(plan, report, "0p", enabled=True, now=11)
    assert len(mouse.clicks) == 3
    assert not controller.observe("game", declaration(), now=12)
    assert controller.snapshot()["status"] == "awaiting_confirmation"
    assert controller.observe("game", {"name": "ActionDealTile", "step": 2, "source": "live",
                                      "data": {"liqi": {"seat": 0, "score": 24000}}}, now=12)
    assert controller.snapshot()["status"] == "idle"


def test_unoffered_discard_and_changed_offer_are_rejected():
    report, profile = offer()
    with pytest.raises(ValueError, match="offered"): plan_riichi(report, profile, 0, "5p", now=10)
    profile["operation_types"] = [7]
    with pytest.raises(ValueError, match="layout"): plan_riichi(report, profile, 0, "0p", now=10)


def test_plain_discard_does_not_confirm_riichi():
    report, profile = offer(); controller = InputController(Mouse())
    controller.submit(plan_riichi(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    assert not controller.observe("game", declaration(False), now=12)
    assert controller.snapshot()["status"] == "blocked"


def test_rejected_declaration_blocks_controller():
    report, profile = offer(); controller = InputController(Mouse())
    controller.submit(plan_riichi(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    controller.observe("game", declaration(), now=12)
    assert not controller.observe("game", {"name": "ActionHule", "step": 2, "source": "live",
                                  "data": {"failed_liqi": {"seat": 0}}}, now=12)
    assert controller.snapshot()["status"] == "blocked"


def test_failed_acceptance_flag_does_not_unlock_input():
    report, profile = offer(); controller = InputController(Mouse())
    controller.submit(plan_riichi(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    controller.observe("game", declaration(), now=12)
    assert not controller.observe("game", {"name": "ActionDealTile", "step": 2, "source": "live",
                           "data": {"liqi": {"seat": 0, "failed": True}}}, now=12)
    assert controller.snapshot()["status"] == "blocked"



def test_ron_on_declaration_discard_resolves_input_without_accepting_riichi():
    report,profile=offer();controller=InputController(Mouse())
    controller.submit(plan_riichi(report,profile,0,'0p',now=10),report,enabled=True,now=11)
    controller.observe('game',declaration(),now=12)
    assert controller.observe('game',{'name':'ActionHule','source':'live','step':2,
        'data':{'failed_liqi':{'seat':0},'hules':[{'seat':1,'hu_tile':'0p','zimo':False}]}},now=12)
    assert controller.snapshot()['status']=='idle'


def test_duplicate_riichi_candidates_are_alternatives_not_tile_copy_requirements():
    report,profile=offer()
    report["state"]["hand"]=["0p","5p"]
    profile.update(hand_count=2,slots=[[.4,.9],[.5,.9]])
    report["state"]["operations"]["operation_list"][1]["combination"]=["0p","5p","5p","0p"]
    plan=plan_riichi(report,profile,0,"0p",now=10)
    assert plan.allowed_tiles==("0p","5p")
    controller=InputController(Mouse())
    controller.submit(plan,report,enabled=True,now=10)
    controller.select_riichi_discard(plan,report,["0p","5p"],enabled=True,now=11)
    assert controller.riichi_phase()=="tile_selected"
