import pytest

from games.balatro.live import (
    BalatroBotRpcError,
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


class DelayedBlindBridge:

    def __init__(self, failures=2, message="select() called with no blind on deck"):
        self.failures = failures
        self.message = message
        self.attempts = 0

    def request(self, method, params=None):
        assert method == "select"
        self.attempts += 1

        if self.attempts <= self.failures:
            raise BalatroBotRpcError(
                -32603,
                self.message,
            )

        return LiveBalatroSnapshot(
            sequence=self.attempts,
            phase="SELECTING_HAND",
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


def test_lifecycle_waits_for_blind_selection_readiness():
    bridge = DelayedBlindBridge(failures=2)
    lifecycle = BalatroLiveLifecycle(
        bridge,
        select_retries=3,
        select_retry_delay=0,
    )

    snapshot = lifecycle.select_blind()

    assert snapshot.phase == "SELECTING_HAND"
    assert bridge.attempts == 3


def test_lifecycle_does_not_retry_unrelated_select_error():
    bridge = DelayedBlindBridge(
        failures=1,
        message="unexpected select failure",
    )
    lifecycle = BalatroLiveLifecycle(
        bridge,
        select_retries=3,
        select_retry_delay=0,
    )

    with pytest.raises(BalatroBotRpcError):
        lifecycle.select_blind()

    assert bridge.attempts == 1


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
