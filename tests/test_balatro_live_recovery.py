import pytest

from games.balatro.live import (
    BalatroBotConnectionError,
    BalatroBotRpcError,
    BalatroLiveRecovery,
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class Bridge:

    def __init__(self):
        self.observe_results = []
        self.send_error = None
        self.request_error = None
        self.sent = []
        self.requests = []

    def observe(self):
        result = self.observe_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def send(self, command):
        self.sent.append(command)
        if self.send_error:
            raise self.send_error

    def request(self, method, params=None):
        self.requests.append((method, params))
        if self.request_error:
            raise self.request_error
        return LiveBalatroSnapshot(
            sequence=2,
            phase="SHOP",
            state_complete=True,
        )


def snapshot(sequence=1, phase="SELECTING_HAND"):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
    )


def test_recovery_retries_observation_connection_failures():
    bridge = Bridge()
    bridge.observe_results = [
        BalatroBotConnectionError("offline"),
        snapshot(),
    ]
    recovery = BalatroLiveRecovery(
        bridge,
        connection_retries=1,
        retry_delay=0,
    )

    assert recovery.observe().phase == "SELECTING_HAND"


def test_recovery_refreshes_after_invalid_state_without_replaying_action():
    bridge = Bridge()
    bridge.send_error = BalatroBotRpcError(
        -32002,
        "invalid state",
        {"name": "INVALID_STATE"},
    )
    bridge.observe_results = [snapshot(4, "SHOP")]
    recovery = BalatroLiveRecovery(
        bridge,
        retry_delay=0,
    )
    command = LiveBalatroCommand(
        sequence=3,
        action="PLAY_CARDS",
    )

    result = recovery.send(command)

    assert result.phase == "SHOP"
    assert bridge.sent == [command]


def test_recovery_refreshes_after_uncertain_connection_failure():
    bridge = Bridge()
    bridge.send_error = BalatroBotConnectionError("lost response")
    bridge.observe_results = [snapshot(5, "SELECTING_HAND")]
    recovery = BalatroLiveRecovery(
        bridge,
        retry_delay=0,
    )

    result = recovery.send(
        LiveBalatroCommand(
            sequence=4,
            action="DISCARD_CARDS",
        )
    )

    assert result.sequence == 5
    assert len(bridge.sent) == 1


def test_recovery_does_not_hide_not_allowed_errors():
    bridge = Bridge()
    bridge.request_error = BalatroBotRpcError(
        -32003,
        "not allowed",
        {"name": "NOT_ALLOWED"},
    )
    recovery = BalatroLiveRecovery(bridge)

    with pytest.raises(BalatroBotRpcError):
        recovery.request("skip")
