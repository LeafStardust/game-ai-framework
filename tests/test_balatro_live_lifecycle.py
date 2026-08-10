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
            "start": "BLIND_SELECT",
            "menu": "MENU",
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


def test_lifecycle_starts_red_deck_white_stake_by_default():
    bridge = Bridge()
    lifecycle = BalatroLiveLifecycle(bridge)

    snapshot = lifecycle.start_run()

    assert snapshot.phase == "BLIND_SELECT"
    assert bridge.methods == [
        (
            "start",
            {
                "deck": "RED",
                "stake": "WHITE",
            },
        )
    ]


def test_lifecycle_can_start_seeded_run():
    bridge = Bridge()
    lifecycle = BalatroLiveLifecycle(bridge)

    lifecycle.start_run(seed="TEST123")

    assert bridge.methods[0][1]["seed"] == "TEST123"


def test_lifecycle_restart_returns_to_menu_before_start():
    bridge = Bridge()
    lifecycle = BalatroLiveLifecycle(bridge)

    snapshot = lifecycle.restart_run()

    assert snapshot.phase == "BLIND_SELECT"
    assert bridge.methods == [
        ("menu", None),
        (
            "start",
            {
                "deck": "RED",
                "stake": "WHITE",
            },
        ),
    ]


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
