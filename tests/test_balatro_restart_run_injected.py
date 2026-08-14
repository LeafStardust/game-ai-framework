from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_memory_restart_run_injected import (
    DEFAULT_RESTART_TIMEOUT_SECONDS,
    LiveRunRestartError,
    _snapshot_diagnostic,
    restart_fresh_unseeded_run,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, phase, *, deck="RED", stake="WHITE", won=False, complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=complete,
        payload={
            "deck": deck,
            "stake": stake,
            "won": won,
            "ante": 1,
        },
    )


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.index = 0

    def observe(self):
        if self.index < len(self.snapshots) - 1:
            value = self.snapshots[self.index]
            self.index += 1
            return value
        return self.snapshots[-1]


class _Bridge:
    def __init__(self, *, callback="START_RUN_PRESENT"):
        self.callback = callback
        self.restart_calls = 0
        self.status_calls = 0

    def status(self):
        self.status_calls += 1
        return {
            "bridge": "1",
            "achievement_gate": "ENABLED",
            "restart_run_callback": self.callback,
        }

    def restart_run(self):
        self.restart_calls += 1


def test_restart_default_timeout_allows_native_wipe_and_setup_animation():
    assert DEFAULT_RESTART_TIMEOUT_SECONDS == 20.0


def test_restart_waits_for_settled_same_identity_blind_select():
    before = _snapshot(10, "GAME_OVER")
    transient = _snapshot(11, "GAME_OVER", complete=False)
    first = _snapshot(12, "BLIND_SELECT")
    stable = _snapshot(13, "BLIND_SELECT")
    observer = _Observer([before, transient, first, stable])
    bridge = _Bridge()
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    result = restart_fresh_unseeded_run(
        runner,
        "RED",
        "WHITE",
        timeout_seconds=0.2,
        poll_interval_seconds=0,
    )

    assert result.before is before
    assert result.after is stable
    assert bridge.status_calls == 1
    assert bridge.restart_calls == 1


def test_restart_rejects_non_game_over_before_command():
    observer = _Observer([_snapshot(10, "SELECTING_HAND")])
    bridge = _Bridge()
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="requires GAME_OVER"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=0.1,
            poll_interval_seconds=0,
        )

    assert bridge.status_calls == 0
    assert bridge.restart_calls == 0


def test_restart_rejects_won_terminal_before_command():
    observer = _Observer([_snapshot(10, "GAME_OVER", won=True)])
    bridge = _Bridge()
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="won runs"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=0.1,
            poll_interval_seconds=0,
        )

    assert bridge.restart_calls == 0


def test_restart_fails_closed_if_bridge_callback_is_not_reported():
    observer = _Observer([_snapshot(10, "GAME_OVER")])
    bridge = _Bridge(callback="MISSING")
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="START_RUN_PRESENT"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=0.1,
            poll_interval_seconds=0,
        )

    assert bridge.restart_calls == 0


def test_restart_fails_closed_on_changed_deck_or_stake_after_command():
    observer = _Observer(
        [
            _snapshot(10, "GAME_OVER"),
            _snapshot(11, "BLIND_SELECT", stake="RED"),
        ]
    )
    bridge = _Bridge()
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="changed deck/stake"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=0.1,
            poll_interval_seconds=0,
        )

    assert bridge.restart_calls == 1


def test_restart_timeout_diagnostic_reports_last_authoritative_snapshot():
    snapshot = _snapshot(14, "BLIND_SELECT", complete=False)

    assert _snapshot_diagnostic(snapshot) == (
        "last_phase=BLIND_SELECT; "
        "last_state_complete=False; "
        "last_sequence=14; "
        "last_identity=RED/WHITE"
    )


def test_bridge_restart_method_emits_control_command_without_payload():
    calls = []
    bridge = object.__new__(FirstPartyBalatroBridge)
    bridge._call = lambda action, indices=(): calls.append((action, tuple(indices)))

    bridge.restart_run()

    assert calls == [("RESTART_RUN", ())]
