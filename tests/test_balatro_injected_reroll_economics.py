from __future__ import annotations

from games.balatro.actions import REFRESH_SHOP, BalatroAction
from games.balatro.live.external.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, *, money, label, state_complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=state_complete,
        payload={
            "money": money,
            "shop_jokers": {
                "cards": [
                    {
                        "area_index": 0,
                        "label": label,
                        "center": f"j_{label.lower()}",
                        "cost": 5,
                    }
                ]
            },
            "shop_boosters": {"cards": []},
            "shop_vouchers": {"cards": []},
        },
    )


class FakeObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        return self.snapshots.pop(0)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def reroll_shop(self):
        self.calls.append(("reroll_shop",))


def test_paid_reroll_waits_past_inventory_change_until_money_settles():
    before = _snapshot(1, money=17, label="Flash")
    inventory_changed = _snapshot(2, money=17, label="Vampire")
    settled = _snapshot(3, money=12, label="Vampire")
    bridge = FakeBridge()

    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(inventory_changed, settled),
        bridge=bridge,
        poll_interval=0,
        reroll_terms_reader=lambda: LiveShopRerollTerms(
            cost=5.0,
            free_rerolls=0,
        ),
    )

    result = dispatcher.dispatch(BalatroAction(REFRESH_SHOP), snapshot=before)

    assert bridge.calls == [("reroll_shop",)]
    assert result.after is settled
    assert result.after.payload["money"] == 12
    assert result.metadata == {"reroll_cost": 5.0, "free_rerolls": 0}


def test_free_reroll_requires_free_count_to_decrease_without_money_change():
    before = _snapshot(10, money=10, label="Flash")
    changed = _snapshot(11, money=10, label="Vampire")
    bridge = FakeBridge()
    terms = iter(
        [
            LiveShopRerollTerms(cost=5.0, free_rerolls=1),
            LiveShopRerollTerms(cost=6.0, free_rerolls=0),
        ]
    )

    dispatcher = LiveMemoryInjectedActionDispatcher(
        FakeObserver(changed),
        bridge=bridge,
        poll_interval=0,
        reroll_terms_reader=lambda: next(terms),
    )

    result = dispatcher.dispatch(BalatroAction(REFRESH_SHOP), snapshot=before)

    assert bridge.calls == [("reroll_shop",)]
    assert result.after is changed
    assert result.after.payload["money"] == 10
    assert result.metadata == {"reroll_cost": 5.0, "free_rerolls": 1}
