import pytest

from games.mahjong_soul.live.runtime.input import plan_discard, DiscardExecutor
from games.mahjong_soul.live.runtime.reader import GameReader
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper
from tests.mahjong_soul.test_reader_monitor import record


def inputs():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"0p")))))
    reader.connections["game"][1].operations = {"seat": 0, "operation_list": [{"type": 1}]}
    return reader.snapshot(), {"version": 1, "verified": True, "client_size": [1280, 720],
                               "hand_count": 1, "slots": [[0.5, 0.9]]}


class Mouse:
    def __init__(self):
        self.clicks = []
    def click(self, *args):
        self.clicks.append(args)


def test_click_is_opt_in_and_confirmed_only_by_matching_live_discard():
    report, profile = inputs()
    plan = plan_discard(report, profile, 0, "0p", now=10)
    mouse = Mouse()
    executor = DiscardExecutor(mouse)
    with pytest.raises(ValueError, match="disabled"):
        executor.execute(plan, report, now=10)
    executor.execute(plan, report, enabled=True, now=11)
    assert mouse.clicks == [(0.5, 0.9, 1280, 720)]
    event = {"name": "ActionDiscardTile", "step": 1, "source": "live", "data": {"seat": 0, "tile": "0p"}}
    assert not executor.observe("other", event)
    assert not executor.observe("game", dict(event, source="restore"))
    assert not executor.observe("game", dict(event, data={"seat": 0, "tile": "5p"}))
    assert executor.observe("game", event)
    assert executor.pending is None
    with pytest.raises(ValueError, match="already"):
        executor.execute(plan, report, enabled=True, now=11)


def test_stale_or_expired_plan_never_clicks():
    report, profile = inputs()
    plan = plan_discard(report, profile, 0, "0p", now=10)
    mouse = Mouse()
    executor = DiscardExecutor(mouse)
    with pytest.raises(ValueError, match="expired"):
        executor.execute(plan, report, enabled=True, now=12)
    report["state"]["step"] = 1
    with pytest.raises(ValueError, match="changed"):
        executor.execute(plan, report, enabled=True, now=11)
    assert not mouse.clicks


@pytest.mark.parametrize("change", ["unverified", "wrong_hand", "outside", "no_operation", "wrong_seat", "not_ready"])
def test_invalid_mapping_or_operation_is_rejected(change):
    report, profile = inputs()
    if change == "unverified": profile["verified"] = False
    if change == "wrong_hand": profile["hand_count"] = 2
    if change == "outside": profile["slots"] = [[1.1, 0.9]]
    if change == "no_operation": report["state"]["operations"] = None
    if change == "wrong_seat": report["state"]["operations"]["seat"] = 1
    if change == "not_ready": report["state_ready"] = False
    with pytest.raises(ValueError):
        plan_discard(report, profile, 0, "0p", now=10)


def test_failed_backend_is_not_retried_and_blocks_further_clicks():
    class Failure:
        def click(self, *args):
            raise OSError("partial input")
    report, profile = inputs()
    plan = plan_discard(report, profile, 0, "0p", now=10)
    executor = DiscardExecutor(Failure())
    with pytest.raises(OSError):
        executor.execute(plan, report, enabled=True, now=11)
    with pytest.raises(ValueError, match="awaiting"):
        executor.execute(plan, report, enabled=True, now=11)


def test_explicit_visual_selection_confirmation_requires_fresh_matching_plan():
    report, profile = inputs()
    mouse = Mouse()
    executor = DiscardExecutor(mouse)
    first = plan_discard(report, profile, 0, "0p", now=10)
    executor.execute(first, report, enabled=True, now=11)
    refreshed = plan_discard(report, profile, 0, "0p", now=20)
    with pytest.raises(ValueError, match="selected tile"):
        executor.confirm_selection(refreshed, report, "5p", enabled=True, now=21)
    executor.confirm_selection(refreshed, report, "0p", enabled=True, now=21)
    assert len(mouse.clicks) == 2
    with pytest.raises(ValueError):
        executor.confirm_selection(refreshed, report, "0p", enabled=True, now=21)
    assert executor.observe("game", {"name": "ActionDiscardTile", "step": 1,
                           "source": "live", "data": {"seat": 0, "tile": "0p"}})


def test_selection_confirmation_rejects_changed_board():
    report, profile = inputs()
    mouse = Mouse()
    executor = DiscardExecutor(mouse)
    plan = plan_discard(report, profile, 0, "0p", now=10)
    executor.execute(plan, report, enabled=True, now=11)
    report["state"]["step"] += 1
    with pytest.raises(ValueError, match="changed"):
        executor.confirm_selection(plan, report, "0p", enabled=True, now=11)
    assert len(mouse.clicks) == 1


def test_partial_input_failure_cannot_be_confirmed_as_selection():
    class Failure:
        def click(self, *args): raise OSError("partial input")
    report, profile = inputs()
    executor = DiscardExecutor(Failure())
    plan = plan_discard(report, profile, 0, "0p", now=10)
    with pytest.raises(OSError): executor.execute(plan, report, enabled=True, now=11)
    with pytest.raises(ValueError, match="No delivered"):
        executor.confirm_selection(plan, report, "0p", enabled=True, now=11)
