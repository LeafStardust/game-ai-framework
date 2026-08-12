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
from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.live.external.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.injected.action_dispatcher import _reroll_complete
from games.balatro.live.injected.install import asset_dir
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
    before = _snapshot(
        7,
        "SHOP",
        money=10,
        shop_jokers={
            "cards": [
                {
                    "area_index": 0,
                    "live_id": 1,
                    "label": "Joker",
                    "center": "j_joker",
                    "cost": 2,
                }
            ]
        },
    )
    after = _snapshot(
        8,
        "SHOP",
        money=9,
        shop_jokers={
            "cards": [
                {
                    "area_index": 0,
                    "live_id": 2,
                    "label": "Greedy Joker",
                    "center": "j_greedy_joker",
                    "cost": 5,
                }
            ]
        },
    )
    bridge = FakeBridge()
    terms = iter(
        [
            LiveShopRerollTerms(cost=1, free_rerolls=0),
            LiveShopRerollTerms(cost=2, free_rerolls=0),
        ]
    )
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
        reroll_terms_reader=lambda: next(terms),
    )

    result = dispatcher.dispatch(BalatroAction(REFRESH_SHOP), snapshot=before)

    assert bridge.calls == [("reroll_shop",)]
    assert result.after is after


def test_injected_reroll_accepts_free_inventory_change():
    before = _snapshot(
        12,
        "SHOP",
        money=10,
        shop_jokers={
            "cards": [
                {
                    "area_index": 0,
                    "live_id": 1,
                    "label": "Joker",
                    "center": "j_joker",
                    "cost": 2,
                }
            ]
        },
    )
    after = _snapshot(
        13,
        "SHOP",
        money=10,
        shop_jokers={
            "cards": [
                {
                    "area_index": 0,
                    "live_id": 2,
                    "label": "Greedy Joker",
                    "center": "j_greedy_joker",
                    "cost": 5,
                }
            ]
        },
    )
    before_terms = LiveShopRerollTerms(cost=5, free_rerolls=1)
    after_terms = LiveShopRerollTerms(cost=6, free_rerolls=0)

    assert _reroll_complete(before, after, before_terms, after_terms)


def test_injected_reroll_rejects_sequence_only_change():
    shop = {
        "cards": [
            {
                "area_index": 0,
                "live_id": 1,
                "label": "Joker",
                "center": "j_joker",
                "cost": 2,
            }
        ]
    }
    before = _snapshot(14, "SHOP", money=10, shop_jokers=shop)
    after = _snapshot(15, "SHOP", money=10, shop_jokers=shop)
    before_terms = LiveShopRerollTerms(cost=1, free_rerolls=0)
    after_terms = LiveShopRerollTerms(cost=2, free_rerolls=0)

    assert not _reroll_complete(before, after, before_terms, after_terms)


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


def test_injected_dispatcher_booster_purchase_waits_for_native_pack():
    item = {"area_index": 1, "label": "Arcana Pack", "cost": 4}
    before = _snapshot(
        20,
        "SHOP",
        money=10,
        shop_boosters={"cards": [{"cost": 2}, item]},
    )
    after = _snapshot(21, "TAROT_PACK", money=6)
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
    assert result.after.phase == "TAROT_PACK"


@pytest.mark.parametrize(
    "phase",
    [
        "TAROT_PACK",
        "PLANET_PACK",
        "SPECTRAL_PACK",
        "STANDARD_PACK",
        "BUFFOON_PACK",
    ],
)
def test_injected_dispatcher_multi_pick_pack_select_accepts_native_pack_phases(phase):
    before = _snapshot(30, phase)
    after = _snapshot(31, phase)
    bridge = FakeBridge()
    terms = iter(
        [
            LivePackSelectionTerms(
                choices_remaining=2,
                choice_addresses=(100, 101, 102),
            ),
            LivePackSelectionTerms(
                choices_remaining=1,
                choice_addresses=(100, 101),
            ),
        ]
    )
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
        pack_terms_reader=lambda: next(terms),
    )

    result = dispatcher.dispatch(
        BalatroAction(SELECT_PACK_CARD, target={"area_index": 2}),
        snapshot=before,
    )

    assert bridge.calls == [("select_pack_card", 2)]
    assert result.after is after
    assert result.details["choices_remaining_before"] == 2
    assert result.details["selected_address"] == 102


def test_injected_dispatcher_single_pack_select_waits_for_shop():
    before = _snapshot(32, "PLANET_PACK")
    transient = _snapshot(33, "PLANET_PACK")
    after = _snapshot(34, "SHOP")
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(transient, after),
        bridge=bridge,
        poll_interval=0,
        pack_terms_reader=lambda: LivePackSelectionTerms(
            choices_remaining=1,
            choice_addresses=(200, 201, 202),
        ),
    )

    result = dispatcher.dispatch(
        BalatroAction(SELECT_PACK_CARD, target={"area_index": 1}),
        snapshot=before,
    )

    assert bridge.calls == [("select_pack_card", 1)]
    assert result.after is after
    assert result.after.phase == "SHOP"


def test_injected_dispatcher_pack_skip_waits_for_shop():
    before = _snapshot(40, "STANDARD_PACK")
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


def test_bridge_asset_uses_native_pack_states_and_normal_callbacks():
    lua = (asset_dir() / "bridge.lua").read_text(encoding="utf-8")

    assert "SMODS_BOOSTER_OPENED" not in lua
    for phase in (
        "TAROT_PACK",
        "PLANET_PACK",
        "SPECTRAL_PACK",
        "STANDARD_PACK",
        "BUFFOON_PACK",
    ):
        assert phase in lua
    for callback in (
        "G.FUNCS.cash_out",
        "G.FUNCS.toggle_shop",
        "G.FUNCS.reroll_shop",
        "G.FUNCS.buy_from_shop",
        "G.FUNCS.use_card",
        "G.FUNCS.skip_booster",
    ):
        assert callback in lua
