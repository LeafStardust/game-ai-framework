from pathlib import Path

import pytest

from games.balatro.actions import SELL_CONSUMABLE, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.install import bridge_asset_path
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, phase, consumables):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"consumables": {"cards": list(consumables)}},
    )


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Bridge:
    def __init__(self):
        self.sold = []

    def sell_consumable(self, index):
        self.sold.append(index)


def test_first_party_bridge_encodes_zero_based_consumable_index(tmp_path):
    bridge = FirstPartyBalatroBridge(tmp_path)
    calls = []
    bridge._call = lambda action, indices=(): calls.append((action, tuple(indices)))

    bridge.sell_consumable(1)

    assert calls == [("SELL_CONSUMABLE", (1,))]


@pytest.mark.parametrize("phase", ["SHOP", "ARCANA_PACK"])
def test_dispatcher_sells_consumable_and_reconciles_live_identity(phase):
    sold = {"live_id": 101, "label": "The Fool"}
    kept = {"live_id": 202, "label": "The Hermit"}
    before = _snapshot(10, phase, [sold, kept])
    after = _snapshot(11, phase, [kept])
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(after),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SELL_CONSUMABLE, target=0),
        snapshot=before,
    )

    assert bridge.sold == [0]
    assert result.after is after
    assert result.details["item"] == sold


def test_dispatcher_rejects_consumable_sale_outside_shop_or_pack():
    before = _snapshot(20, "SELECTING_HAND", [{"live_id": 101}])
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(before),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="requires SHOP or an open pack"):
        dispatcher.dispatch(
            BalatroAction(SELL_CONSUMABLE, target=0),
            snapshot=before,
        )

    assert bridge.sold == []


def test_injected_lua_bridge_routes_consumable_sale_through_native_callback():
    asset = bridge_asset_path().read_text(encoding="utf-8")

    block = asset[
        asset.index("local function execute_sell_consumable") :
        asset.index("local function execute_reorder_jokers")
    ]
    assert 'action == "SELL_CONSUMABLE"' in asset
    assert "G.consumeables.cards[index + 1]" in block
    assert "G.FUNCS and G.FUNCS.sell_card" in block
    assert "is_pack_state()" in block
