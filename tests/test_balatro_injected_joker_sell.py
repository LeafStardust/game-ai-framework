from __future__ import annotations

from pathlib import Path

import pytest

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(
    sequence: int,
    phase: str,
    jokers: list[dict],
    *,
    boss_name: str | None = None,
    hand: list[dict] | None = None,
) -> LiveBalatroSnapshot:
    payload = {
        "jokers": {"cards": jokers},
        "hand": {"cards": list(hand or [])},
    }
    if boss_name is not None:
        payload["blind"] = {"type": "BOSS", "name": boss_name}
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload=payload,
    )


class FakeObserver:
    def __init__(self, *snapshots: LiveBalatroSnapshot) -> None:
        self.snapshots = list(snapshots)
        self.last = snapshots[-1]

    def observe(self) -> LiveBalatroSnapshot:
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class FakeBridge:
    def __init__(self) -> None:
        self.sold: list[int] = []

    def sell_joker(self, index: int) -> None:
        self.sold.append(index)


def test_first_party_bridge_encodes_zero_based_joker_index(tmp_path):
    bridge = FirstPartyBalatroBridge(tmp_path)
    calls = []
    bridge._call = lambda action, indices=(): calls.append((action, tuple(indices)))

    bridge.sell_joker(2)

    assert calls == [("SELL_JOKER", (2,))]


def test_injected_dispatcher_sells_joker_and_reconciles_live_identity():
    sold = {"live_id": 101, "label": "Joker", "sell_cost": 2}
    kept = {"live_id": 202, "label": "Misprint", "sell_cost": 2}
    before = _snapshot(10, "SHOP", [sold, kept])
    after = _snapshot(11, "SHOP", [kept])
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SELL_JOKER, target=0),
        snapshot=before,
    )

    assert bridge.sold == [0]
    assert result.before is before
    assert result.after is after
    assert result.details["area_index"] == 0
    assert result.details["item"] == sold


def test_injected_dispatcher_rejects_joker_sale_outside_shop():
    before = _snapshot(20, "SELECTING_HAND", [{"live_id": 101}])
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(before),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="requires SHOP"):
        dispatcher.dispatch(
            BalatroAction(SELL_JOKER, target=0),
            snapshot=before,
        )

    assert bridge.sold == []


def test_injected_dispatcher_sells_during_verdant_leaf_and_waits_for_debuff_lift():
    sold = {"live_id": 101, "label": "Joker", "sell_cost": 2}
    kept = {"live_id": 202, "label": "Misprint", "sell_cost": 2}
    before = _snapshot(
        20,
        "SELECTING_HAND",
        [sold, kept],
        boss_name="Verdant Leaf",
        hand=[{"live_id": 1, "debuff": True}],
    )
    after = _snapshot(
        21,
        "SELECTING_HAND",
        [kept],
        boss_name="Verdant Leaf",
        hand=[{"live_id": 1, "debuff": False}],
    )
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(after),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SELL_JOKER, target=0),
        snapshot=before,
    )

    assert bridge.sold == [0]
    assert result.after is after


def test_injected_dispatcher_rejects_out_of_range_joker_index():
    before = _snapshot(30, "SHOP", [{"live_id": 101}])
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(before),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    with pytest.raises(UnsupportedInjectedAction, match="out of range"):
        dispatcher.dispatch(
            BalatroAction(SELL_JOKER, target=1),
            snapshot=before,
        )

    assert bridge.sold == []


def test_injected_lua_bridge_routes_sell_joker_through_native_callback():
    asset = (
        Path(__file__).parents[1]
        / "games"
        / "balatro"
        / "live"
        / "injected"
        / "assets"
        / "bridge.lua"
    ).read_text(encoding="utf-8")

    assert 'action == "SELL_JOKER"' in asset
    assert "G.FUNCS and G.FUNCS.sell_card" in asset
    assert "G.jokers.cards[index + 1]" in asset
    assert 'blind.name == "Verdant Leaf"' in asset
    assert 'require_state("SHOP")' not in asset[
        asset.index("local function execute_sell_joker") :
        asset.index("local function execute_reorder_jokers")
    ]
