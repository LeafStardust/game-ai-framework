from games.balatro.live import (
    BalatroLiveLifecycle,
    LiveBalatroSnapshot,
)


class Bridge:

    def __init__(self):
        self.methods = []

    def request(self, method, params=None):
        self.methods.append((method, params))
        phases = {
            "select": "SELECTING_HAND",
            "skip": "BLIND_SELECT",
            "cash_out": "SHOP",
            "next_round": "BLIND_SELECT",
        }
        return LiveBalatroSnapshot(
            sequence=len(self.methods),
            phase=phases[method],
            state_complete=True,
        )


def test_lifecycle_selects_and_skips_blinds():
    bridge = Bridge()
    lifecycle = BalatroLiveLifecycle(bridge)

    selected = lifecycle.select_blind()
    skipped = lifecycle.skip_blind()

    assert selected.phase == "SELECTING_HAND"
    assert skipped.phase == "BLIND_SELECT"
    assert bridge.methods == [
        ("select", None),
        ("skip", None),
    ]


def test_lifecycle_cashes_out_and_advances_round():
    bridge = Bridge()
    lifecycle = BalatroLiveLifecycle(bridge)

    shop = lifecycle.cash_out()
    blind_select = lifecycle.next_round()

    assert shop.phase == "SHOP"
    assert blind_select.phase == "BLIND_SELECT"
    assert bridge.methods == [
        ("cash_out", None),
        ("next_round", None),
    ]
