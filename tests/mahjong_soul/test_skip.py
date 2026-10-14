from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.skip import plan_skip
from games.mahjong_soul.live.runtime.controller import InputController
from tests.mahjong_soul.test_calls import chi_offer
from tests.mahjong_soul.test_input import Mouse


def setup():
    report, _ = chi_offer()
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "stage": "call_offer", "operation_types": [2], "skip": [0.67, 0.77]}
    mouse = Mouse(); controller = InputController(mouse)
    controller.submit(plan_skip(report, profile, now=10), report, enabled=True, now=11)
    return report, mouse, controller


def request(cancel=True):
    return {"method": ".lq.FastTest.inputChiPengGang", "kind": "request", "request_id": 78, "data": {"cancel_operation": cancel}}


def response(code=0):
    return {"method": ".lq.FastTest.inputChiPengGang", "kind": "response", "request_id": 78, "data": {"error": {"code": code}}}


def test_skip_requires_client_cancellation_and_matching_server_reply():
    report, mouse, controller = setup()
    assert not controller.observe_message("game", response(), False, now=12)
    assert not controller.observe_message("game", request(False), True, now=12)
    assert not controller.observe_message("other", request(), True, now=12)
    assert not controller.observe_message("game", request(), False, now=12)
    assert not controller.observe_message("game", request(), True, now=12)
    wrong = response(); wrong["request_id"] = 79
    assert not controller.observe_message("game", wrong, False, now=12)
    assert controller.observe_message("game", response(), False, now=12)
    assert controller.snapshot()["status"] == "idle"
    assert len(mouse.clicks) == 1


def test_rejected_skip_blocks_controller():
    _, _, controller = setup()
    controller.observe_message("game", request(), True, now=12)
    assert not controller.observe_message("game", response(100), False, now=12)
    assert controller.snapshot()["status"] == "blocked"


def test_later_game_action_does_not_confirm_skip():
    _, _, controller = setup()
    assert not controller.observe("game", {"name": "ActionDealTile", "step": 1, "source": "live", "data": {"seat": 0}}, now=12)
    assert controller.snapshot()["status"] == "awaiting_confirmation"


@pytest.mark.parametrize("bad", ["profile_stage", "wrong_offer", "discard"] )
def test_skip_rejects_wrong_ui_context(bad):
    report, _ = chi_offer()
    profile = {"version": 1, "verified": True, "client_size": [925, 520],
               "stage": "call_offer", "operation_types": [2], "skip": [0.67, 0.77]}
    if bad == "profile_stage": profile["stage"] = "chi_choices"
    if bad == "wrong_offer": profile["operation_types"] = [2, 3]
    if bad == "discard": report["state"]["operations"]["operation_list"][0]["type"] = 1
    with pytest.raises(ValueError): plan_skip(report, profile, now=10)


@pytest.mark.parametrize("case", ["accepted", "rejected", "advanced"])
def test_reader_clears_only_the_acknowledged_current_call_offer(case):
    from games.mahjong_soul.live.external.schema import LiqiSchema
    from games.mahjong_soul.live.runtime.reader import GameReader
    from tests.mahjong_soul.test_decoder_state import schema, wrapper, action, blob
    from tests.mahjong_soul.test_reader_monitor import record
    document = schema().document
    nested = document["nested"]["lq"]["nested"]
    nested["ReqCall"] = {"fields": {"cancel_operation": {"id": 3, "type": "bool"}}}
    nested["Error"] = {"fields": {"code": {"id": 1, "type": "uint32"}}}
    nested["ResCall"] = {"fields": {"error": {"id": 1, "type": "Error"}}}
    nested["FastTest"]["methods"]["inputChiPengGang"] = {"requestType": "ReqCall", "responseType": "ResCall"}
    reader = GameReader(LiqiSchema(document), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    state = reader.connections["game"][1]
    state.operations = {"seat": 0, "operation_list": [{"type": 2}]}
    reader.consume(record(wrapper(2, ".lq.FastTest.inputChiPengGang", b"\x18\x01", request_id=78), client=True))
    if case == "advanced":
        state.last_step = 1
        state.operations = {"seat": 0, "operation_list": [{"type": 1}]}
    payload = blob(1, b"\x08\x64") if case == "rejected" else b""
    reader.consume(record(wrapper(3, "", payload, request_id=78)))
    assert (reader.snapshot()["state"]["operations"] is None) == (case == "accepted")
