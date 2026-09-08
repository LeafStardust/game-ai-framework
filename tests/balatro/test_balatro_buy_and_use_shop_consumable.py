from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Bridge:
    def __init__(self):
        self.buy_and_use_calls = []

    def buy_and_use_shop_consumable(self, area_index):
        self.buy_and_use_calls.append(area_index)


def _shop_snapshot(*, sequence, money, cards):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={
            "money": money,
            "shop_jokers": {
                "cards": list(cards),
                "count": len(cards),
                "limit": 2,
            },
        },
    )


def test_buy_and_use_shop_consumable_allows_immediate_money_effect():
    other = {
        "area_index": 0,
        "live_id": 137,
        "label": "Other Item",
        "ability_name": "Mercury",
        "ability_set": "Planet",
        "center": "c_mercury",
        "cost": 3,
    }
    temperance = {
        "area_index": 1,
        "live_id": 139,
        "label": "Temperance",
        "ability_name": "Temperance",
        "ability_set": "Tarot",
        "center": "c_temperance",
        "cost": 3,
    }
    before = _shop_snapshot(
        sequence=10,
        money=13,
        cards=[other, temperance],
    )
    # Temperance is bought for $3 and immediately produces $10, so the settled
    # public money is $20 rather than the ordinary purchase-only $10.
    after = _shop_snapshot(
        sequence=11,
        money=20,
        cards=[other],
    )
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(after),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(
        BalatroAction(
            BUY_AND_USE_CONSUMABLE,
            target={"area_index": 1},
        ),
        snapshot=before,
    )

    assert bridge.buy_and_use_calls == [1]
    assert result.after is after
    assert result.details["area_index"] == 1
    assert result.details["item"]["live_id"] == 139
    assert result.details["consumed_immediately"] is True
