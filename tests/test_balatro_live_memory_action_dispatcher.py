from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_CONSUMABLE,
    SELECT_PACK_CARD,
    BalatroAction,
)
from games.balatro.live.external.live_memory_action_dispatcher import (
    LiveMemoryActionDispatcher,
    UnsupportedExternalLiveAction,
    _target_index,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, phase="SHOP", money=10, offers=None):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "money": money,
            "shop_jokers": {"cards": list(offers or [])},
        },
    )


class Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.last = self.snapshots[-1]

    def observe(self):
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class PurchaseExecutor:
    def __init__(self, before, item):
        self.before = before
        self.item = item
        self.indices = []

    def dispatch(self, index):
        self.indices.append(index)
        return self.before, self.item, "verified-control"


class PackExecutor:
    def __init__(self):
        self.indices = []

    def dispatch(self, index):
        self.indices.append(index)
        return "pack-result"


def _dispatcher(observer, *, buy=None, buy_and_use=None, pack=None):
    unused = object()
    return LiveMemoryActionDispatcher(
        observer,
        mouse=object(),
        window_locator=object(),
        hand_executor=unused,
        buy_executor=buy or unused,
        buy_and_use_executor=buy_and_use or unused,
        special_executor=unused,
        reroll_executor=unused,
        next_round_executor=unused,
        cash_out_executor=unused,
        pack_card_executor=pack or unused,
        pack_skip_executor=unused,
        timeout=0.01,
        poll_interval=0.0,
    )


def test_target_index_accepts_framework_item_area_index():
    assert _target_index(SimpleNamespace(area_index=2)) == 2
    assert _target_index({"area_index": 3}) == 3
    assert _target_index(4) == 4


def test_buy_consumable_routes_area_index_and_requires_shop_postcondition():
    target = SimpleNamespace(area_index=1)
    before = _snapshot(
        4,
        money=10,
        offers=[{"live_id": 77, "label": "Pluto"}],
    )
    after = _snapshot(5, money=7, offers=[])
    item = SimpleNamespace(live_id=77, label="Pluto", cost=3.0)
    executor = PurchaseExecutor(before, item)
    dispatcher = _dispatcher(Observer([after]), buy=executor)

    result = dispatcher.dispatch(
        BalatroAction(BUY_CONSUMABLE, target=target),
        snapshot=before,
    )

    assert executor.indices == [1]
    assert result.before is before
    assert result.after is after
    assert result.details["control"] == "verified-control"


def test_buy_and_use_accepts_phase_change_after_consumption():
    target = SimpleNamespace(area_index=0)
    before = _snapshot(
        8,
        money=7,
        offers=[{"live_id": 88, "label": "Earth"}],
    )
    after = _snapshot(9, phase="PLAY_TAROT", money=4, offers=[])
    item = SimpleNamespace(live_id=88, label="Earth", cost=3.0)
    executor = PurchaseExecutor(before, item)
    dispatcher = _dispatcher(Observer([after]), buy_and_use=executor)

    result = dispatcher.dispatch(
        BalatroAction(BUY_AND_USE_CONSUMABLE, target=target),
        snapshot=before,
    )

    assert executor.indices == [0]
    assert result.after.phase == "PLAY_TAROT"


def test_pack_card_action_routes_index_to_two_click_pack_executor():
    before = _snapshot(2, phase="BUFFOON_PACK", money=4)
    after = _snapshot(3, phase="BUFFOON_PACK", money=4)
    pack = PackExecutor()
    dispatcher = _dispatcher(Observer([after]), pack=pack)

    result = dispatcher.dispatch(
        BalatroAction(SELECT_PACK_CARD, target=1),
        snapshot=before,
    )

    assert pack.indices == [1]
    assert result.details == "pack-result"
    assert result.after is after


def test_unsupported_external_action_fails_closed():
    before = _snapshot(1)
    dispatcher = _dispatcher(Observer([before]))

    with pytest.raises(UnsupportedExternalLiveAction):
        dispatcher.dispatch(BalatroAction("NOT_A_REAL_ACTION"), snapshot=before)
