from __future__ import annotations

import pytest

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.install import asset_dir
from games.balatro.live.protocol import LiveBalatroSnapshot


class _RecordingWireBridge(FirstPartyBalatroBridge):
    def __init__(self):
        self.calls = []

    def _call(self, action, indices=()):
        self.calls.append((action, tuple(indices)))
        return "accepted"


class _RecordingActionBridge:
    def __init__(self):
        self.calls = []

    def buy_and_use_shop_consumable(self, index):
        self.calls.append(("buy_and_use_shop_consumable", index))


class _Observer:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


def _snapshot(sequence, *, money, cards, complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=complete,
        payload={
            "money": money,
            "shop_jokers": {"cards": list(cards)},
        },
    )


def test_first_party_bridge_encodes_buy_and_use_consumable_command():
    bridge = _RecordingWireBridge()

    bridge.buy_and_use_shop_consumable(2)

    assert bridge.calls == [("BUY_AND_USE_CONSUMABLE", (2,))]


def test_injected_dispatcher_buy_and_use_reconciles_consumed_offer_and_money():
    target = {
        "area_index": 0,
        "live_id": 501,
        "label": "The Hermit",
        "ability_set": "Tarot",
        "cost": 3,
    }
    other = {
        "area_index": 1,
        "live_id": 502,
        "label": "Joker",
        "ability_set": "Joker",
        "cost": 2,
    }
    before = _snapshot(10, money=10, cards=[target, other])
    transient = _snapshot(11, money=7, cards=[target, other], complete=False)
    settled = _snapshot(
        12,
        money=7,
        cards=[{**other, "area_index": 0}],
    )
    bridge = _RecordingActionBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(transient, settled),
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(BUY_AND_USE_CONSUMABLE, target={"area_index": 0}),
        snapshot=before,
    )

    assert bridge.calls == [("buy_and_use_shop_consumable", 0)]
    assert result.after is settled
    assert result.details == {
        "area_index": 0,
        "item": target,
        "consumed_immediately": True,
    }


@pytest.mark.parametrize("ability_set", [None, "Joker", "Enhanced"])
def test_injected_dispatcher_buy_and_use_rejects_non_consumable_shop_item(ability_set):
    target = {
        "area_index": 0,
        "live_id": 601,
        "label": "Not a consumable",
        "ability_set": ability_set,
        "cost": 3,
    }
    before = _snapshot(20, money=10, cards=[target])
    bridge = _RecordingActionBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(before),
        bridge=bridge,
        timeout=0,
        poll_interval=0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="Tarot/Planet/Spectral"):
        dispatcher.dispatch(
            BalatroAction(BUY_AND_USE_CONSUMABLE, target={"area_index": 0}),
            snapshot=before,
        )

    assert bridge.calls == []


def test_injected_bridge_asset_uses_native_buy_and_use_control():
    lua = (asset_dir() / "bridge.lua").read_text(encoding="utf-8")

    assert 'action == "BUY_AND_USE_CONSUMABLE"' in lua
    assert "card.children.buy_and_use_button" in lua
    assert 'config.button ~= "buy_from_shop"' in lua
    assert 'config.func ~= "can_buy_and_use"' in lua
    assert "G.FUNCS.buy_from_shop" in lua
