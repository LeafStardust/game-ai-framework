from __future__ import annotations

import threading
import time

import pytest

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_ROUND,
    END_SHOP,
    REFRESH_SHOP,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, phase, *, state_complete=True, money=10, **areas):
    payload = {"money": money}
    payload.update(areas)
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=state_complete,
        payload=payload,
    )


class FakeObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        return self.snapshots.pop(0)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def cash_out(self):
        self.calls.append(("cash_out",))

    def next_round(self):
        self.calls.append(("next_round",))

    def reroll_shop(self):
        self.calls.append(("reroll_shop",))

    def buy_shop_card(self, index):
        self.calls.append(("buy_shop_card", index))

    def buy_voucher(self, index):
        self.calls.append(("buy_voucher", index))

    def buy_booster(self, index):
        self.calls.append(("buy_booster", index))

    def select_pack_card(self, index):
        self.calls.append(("select_pack_card", index))

    def skip_booster(self):
        self.calls.append(("skip_booster",))


def _atomic_response(bridge, text):
    temporary = bridge.response_path.with_name(
        bridge.response_path.name + ".tmp"
    )
    temporary.write_bytes(text.encode("utf-8"))
    temporary.replace(bridge.response_path)


@pytest.mark.parametrize(
    ("method", "args", "expected_action", "expected_payload"),
    [
        ("cash_out", (), "CASH_OUT", ""),
        ("next_round", (), "NEXT_ROUND", ""),
        ("reroll_shop", (), "REROLL_SHOP", ""),
        ("buy_shop_card", (2,), "BUY_CARD", "2"),
        ("buy_voucher", (1,), "BUY_VOUCHER", "1"),
        ("buy_booster", (0,), "BUY_BOOSTER", "0"),
        ("select_pack_card", (3,), "PACK_SELECT", "3"),
        ("skip_booster", (), "PACK_SKIP", ""),
    ],
)
def test_extended_bridge_commands_use_expected_wire_actions(
    tmp_path,
    method,
    args,
    expected_action,
    expected_payload,
):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=1.0,
        poll_interval=0.001,
    )
    captured = {}

    def responder():
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                text = bridge.command_path.read_text(encoding="utf-8")
                command_id, action, payload = text.rstrip("\n").split("\t", 2)
                captured.update(action=action, payload=payload)
                bridge.command_path.unlink()
                _atomic_response(
                    bridge,
                    f"{command_id}\tOK\taccepted\n",
                )
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    getattr(bridge, method)(*args)
    thread.join(timeout=1.0)

    assert captured == {
        "action": expected_action,
        "payload": expected_payload,
    }


def test_injected_dispatcher_cash_out_waits_for_settled_shop():
    before = _snapshot(1, "ROUND_EVAL")
    transient = _snapshot(2, "ROUND_EVAL", state_complete=False)
    after = _snapshot(3, "SHOP", state_complete=True, money=14)
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(transient, after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(END_ROUND), snapshot=before)

    assert bridge.calls == [("cash_out",)]
    assert result.after is after


def test_injected_dispatcher_next_round_waits_for_blind_select():
    before = _snapshot(4, "SHOP")
    after = _snapshot(5, "BLIND_SELECT")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(END_SHOP), snapshot=before)

    assert bridge.calls == [("next_round",)]
    assert result.after.phase == "BLIND_SELECT"


def test_injected_dispatcher_reroll_requires_changed_shop_checkpoint():
    before = _snapshot(7, "SHOP", money=10)
    after = _snapshot(8, "SHOP", money=9)
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(BalatroAction(REFRESH_SHOP), snapshot=before)

    assert bridge.calls == [("reroll_shop",)]
    assert result.after is after


@pytest.mark.parametrize(
    ("action_name", "area_name", "bridge_call"),
    [
        (BUY_JOKER, "shop_jokers", "buy_shop_card"),
        (BUY_CONSUMABLE, "shop_jokers", "buy_shop_card"),
        (BUY_VOUCHER, "shop_vouchers", "buy_voucher"),
    ],
)
def test_injected_dispatcher_shop_purchase_checks_count_and_money(
    action_name,
    area_name,
    bridge_call,
):
    item = {"area_index": 0, "label": "Test", "cost": 3}
    before = _snapshot(
        10,
        "SHOP",
        money=10,
        **{area_name: {"cards": [item]}},
    )
    after = _snapshot(
        11,
        "SHOP",
        money=7,
        **{area_name: {"cards": []}},
    )
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(action_name, target={"area_index": 0}),
        snapshot=before,
    )

    assert bridge.calls == [(bridge_call, 0)]
    assert result.after is after


def test_injected_dispatcher_booster_purchase_waits_for_open_pack():
    item = {"area_index": 1, "label": "Arcana Pack", "cost": 4}
    before = _snapshot(
        20,
        "SHOP",
        money=10,
        shop_boosters={"cards": [{"cost": 2}, item]},
    )
    after = _snapshot(21, "SMODS_BOOSTER_OPENED", money=6)
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(BUY_BOOSTER, target={"area_index": 1}),
        snapshot=before,
    )

    assert bridge.calls == [("buy_booster", 1)]
    assert result.after.phase == "SMODS_BOOSTER_OPENED"


def test_injected_dispatcher_pack_select_accepts_more_choices_checkpoint():
    before = _snapshot(30, "SMODS_BOOSTER_OPENED")
    after = _snapshot(31, "SMODS_BOOSTER_OPENED")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SELECT_PACK_CARD, target={"area_index": 2}),
        snapshot=before,
    )

    assert bridge.calls == [("select_pack_card", 2)]
    assert result.after is after


def test_injected_dispatcher_pack_skip_waits_for_shop():
    before = _snapshot(40, "SMODS_BOOSTER_OPENED")
    after = _snapshot(41, "SHOP")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SKIP_BOOSTER),
        snapshot=before,
    )

    assert bridge.calls == [("skip_booster",)]
    assert result.after.phase == "SHOP"
