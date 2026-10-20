from copy import deepcopy
import pytest

from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import plan_discard
from games.mahjong_soul.live.runtime.calls import plan_pon
from tests.mahjong_soul.test_input import inputs, Mouse
from tests.mahjong_soul.test_calls import offer


def confirmed(tile="0p", step=1):
    return {"name": "ActionDiscardTile", "step": step, "source": "live",
            "data": {"seat": 0, "tile": tile}}


def test_cross_executor_overlap_and_same_step_duplicates_are_blocked():
    report, profile = inputs(); mouse = Mouse(); controller = InputController(mouse)
    controller.submit(plan_discard(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    call_report, call_profile = offer()
    pon = plan_pon(call_report, call_profile, now=10)
    with pytest.raises(ValueError, match="overlapping"):
        controller.submit(pon, call_report, enabled=True, now=11)
    assert controller.observe("game", confirmed(), now=12)
    with pytest.raises(ValueError, match="already attempted"):
        controller.submit(pon, call_report, enabled=True, now=11)
    assert len(mouse.clicks) == 1
    assert controller.snapshot()["status"] == "idle"


def test_preflight_failure_does_not_reserve_step():
    report, profile = inputs(); controller = InputController(Mouse())
    stale = plan_discard(report, profile, 0, "0p", now=10)
    with pytest.raises(ValueError, match="expired"):
        controller.submit(stale, report, enabled=True, now=12)
    assert controller.snapshot()["attempted_steps"] == 0
    fresh = plan_discard(report, profile, 0, "0p", now=12)
    controller.submit(fresh, report, enabled=True, now=13)


def test_timeout_accepts_late_confirmation_without_duplicate_click():
    report, profile = inputs(); mouse = Mouse(); controller = InputController(mouse)
    controller.submit(plan_discard(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    assert controller.update(report, now=16)["status"] == "blocked"
    assert controller.observe("game", confirmed(), now=20)
    assert controller.snapshot()["status"]=="idle" and len(mouse.clicks)==1
    assert controller.was_attempted(report,0)


@pytest.mark.parametrize("failure", ["closed", "new_connection", "incomplete", "wrong_action"])
def test_connection_or_confirmation_uncertainty_stops_input(failure):
    report, profile = inputs(); mouse = Mouse(); controller = InputController(mouse)
    controller.submit(plan_discard(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    if failure == "closed": report["connection_open"] = False
    if failure == "new_connection": report["game_connection"] = "new"
    if failure == "incomplete": report["state_ready"] = False
    if failure == "wrong_action": assert not controller.observe("game", confirmed("5p"), now=12)
    assert controller.update(report, now=12)["status"] == "blocked"
    assert len(mouse.clicks) == 1


def test_partial_delivery_stays_blocked_and_cannot_confirm_selection():
    class Failure:
        def click(self, *args): raise OSError("partial delivery")
    report, profile = inputs(); controller = InputController(Failure())
    plan = plan_discard(report, profile, 0, "0p", now=10)
    with pytest.raises(OSError): controller.submit(plan, report, enabled=True, now=11)
    assert controller.snapshot()["status"] == "blocked"
    with pytest.raises(ValueError): controller.confirm_selection(plan, report, "0p", enabled=True, now=11)


def test_selection_confirmation_uses_same_controller_and_then_allows_next_step():
    report, profile = inputs(); mouse = Mouse(); controller = InputController(mouse)
    plan = plan_discard(report, profile, 0, "0p", now=10)
    controller.submit(plan, report, enabled=True, now=11)
    controller.confirm_selection(plan, report, "0p", enabled=True, now=11)
    assert len(mouse.clicks) == 2
    assert controller.observe("game", confirmed(), now=12)
    report["state"]["step"] = 2
    controller.submit(plan_discard(report, profile, 0, "0p", now=12), report, enabled=True, now=13)
    assert len(mouse.clicks) == 3


@pytest.mark.parametrize("change", ["round", "generation"])
def test_step_zero_is_valid_in_a_new_round_or_game(change):
    report, profile = inputs(); controller = InputController(Mouse())
    controller.submit(plan_discard(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    assert controller.observe("game", confirmed(), now=12)
    if change == "round": report["state"]["round"]["ju"] = 1
    else: report["game_generation"] = 1
    controller.submit(plan_discard(report, profile, 0, "0p", now=13), report, enabled=True, now=14)
    assert controller.snapshot()["attempted_steps"] == 2


def test_late_confirmation_succeeds_without_periodic_update():
    report, profile = inputs(); controller = InputController(Mouse())
    controller.submit(plan_discard(report, profile, 0, "0p", now=10), report, enabled=True, now=11)
    assert controller.observe("game", confirmed(), now=16)
    assert controller.snapshot()["status"] == "idle"


def test_concurrent_submissions_send_only_one_click():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered, release = Event(), Event()
    class SlowMouse(Mouse):
        def click(self, *args):
            self.clicks.append(args)
            entered.set()
            assert release.wait(2)
    report, profile = inputs(); mouse = SlowMouse(); controller = InputController(mouse)
    plan = plan_discard(report, profile, 0, "0p", now=10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(controller.submit, plan, report, enabled=True, now=11)
        assert entered.wait(2)
        second = pool.submit(controller.submit, plan, report, enabled=True, now=11)
        release.set()
        first.result()
        with pytest.raises(ValueError, match="overlapping"): second.result()
    assert len(mouse.clicks) == 1


def test_delayed_visual_confirmation_retains_controller_and_requires_fresh_plan():
    report, profile = inputs(); mouse = Mouse()
    controller = InputController(mouse, confirmation_timeout=300)
    first = plan_discard(report, profile, 0, "0p", now=10)
    controller.submit(first, report, enabled=True, now=10)
    with pytest.raises(ValueError, match="expired"):
        controller.confirm_selection(first, report, "0p", enabled=True, now=150)
    assert len(mouse.clicks) == 1
    fresh = plan_discard(report, profile, 0, "0p", now=150)
    controller.confirm_selection(fresh, report, "0p", enabled=True, now=150)
    assert len(mouse.clicks) == 2
    assert controller.observe("game", confirmed(), now=151)
    assert controller.snapshot()["status"] == "idle"


def test_manual_confirmation_requires_exact_token_and_tile(tmp_path):
    import json
    from games.mahjong_soul.live.runtime.manual_discard import confirmation_matches
    report, profile = inputs()
    plan = plan_discard(report, profile, 0, "0p", now=1)
    path = tmp_path / "ticket.json"
    assert not confirmation_matches(path, plan)
    path.write_text("{", encoding="utf-8")
    assert not confirmation_matches(path, plan)
    path.write_text(json.dumps({"token": "old", "tile": plan.tile}), encoding="utf-8")
    assert not confirmation_matches(path, plan)
    path.write_text(json.dumps({"token": plan.token, "tile": "1m"}), encoding="utf-8")
    assert not confirmation_matches(path, plan)
    path.write_text(json.dumps({"token": plan.token, "tile": plan.tile}), encoding="utf-8")
    assert confirmation_matches(path, plan)


def test_verified_timeout_retry_is_bounded_and_preserves_reservation():
    report,profile=inputs();mouse=Mouse();controller=InputController(mouse)
    controller.submit(plan_discard(report,profile,0,"0p",now=10),report,enabled=True,now=11)
    controller.update(report,now=16)
    fresh=plan_discard(report,profile,0,"0p",now=16)
    with pytest.raises(ValueError):controller.retry_discard(fresh,report,enabled=True,now=16)
    controller.retry_discard(fresh,report,enabled=True,visually_verified=True,now=16)
    assert len(mouse.clicks)==2 and controller.was_attempted(report,0)
    controller.update(report,now=22)
    with pytest.raises(ValueError):controller.retry_discard(plan_discard(report,profile,0,"0p",now=22),report,enabled=True,visually_verified=True,now=22)
    assert len(mouse.clicks)==2
    assert controller.observe("game",confirmed(),now=25)


@pytest.mark.parametrize("change",["board","expired","tile","connection"])
def test_timeout_retry_rejects_changed_or_stale_evidence(change):
    from dataclasses import replace
    report,profile=inputs();mouse=Mouse();controller=InputController(mouse)
    controller.submit(plan_discard(report,profile,0,"0p",now=10),report,enabled=True,now=11)
    controller.update(report,now=16);fresh=plan_discard(report,profile,0,"0p",now=16)
    if change=="board":report["state"]["step"]+=1
    if change=="expired":fresh=replace(fresh,expires=15)
    if change=="tile":fresh=replace(fresh,tile="5p")
    if change=="connection":report["connection_open"]=False
    with pytest.raises(ValueError):controller.retry_discard(fresh,report,enabled=True,visually_verified=True,now=16)
    assert len(mouse.clicks)==1


def test_delivery_failure_cannot_be_cleared_by_late_confirmation():
    class Failure:
        def click(self,*args):raise OSError("partial")
    report,profile=inputs();controller=InputController(Failure())
    with pytest.raises(OSError):controller.submit(plan_discard(report,profile,0,"0p",now=10),report,enabled=True,now=11)
    assert not controller.observe("game",confirmed(),now=20)
    assert controller.snapshot()["status"]=="blocked"
