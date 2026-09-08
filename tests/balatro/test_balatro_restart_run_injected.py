from types import SimpleNamespace

import pytest

from games.balatro.live.runtime.live_memory_restart_run_injected import (
    DEFAULT_RESTART_TIMEOUT_SECONDS,
    LiveRunRestartError,
    _snapshot_diagnostic,
    restart_fresh_unseeded_run,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.install import bridge_asset_path
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
    def __init__(
        self,
        *,
        callback="START_RUN_PRESENT",
        restart_unlock_drain="1",
        restart_pause_release="1",
    ):
        self.callback = callback
        self.restart_unlock_drain = restart_unlock_drain
        self.restart_pause_release = restart_pause_release
        self.restart_calls = 0
        self.status_calls = 0

    def status(self):
        self.status_calls += 1
        return {
            "bridge": "2",
            "achievement_gate": "ENABLED",
            "restart_run_callback": self.callback,
            "restart_unlock_drain": self.restart_unlock_drain,
            "restart_pause_release": self.restart_pause_release,
        }

    def restart_run(self):
        self.restart_calls += 1


def test_restart_default_timeout_allows_slow_native_wipe_unlock_and_setup_animation():
    assert DEFAULT_RESTART_TIMEOUT_SECONDS == 60.0


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


def test_restart_accepts_fresh_run_sequence_counter_reset():
    before = _snapshot(651, "GAME_OVER")
    fresh = _snapshot(1, "BLIND_SELECT")
    observer = _Observer([before, fresh, fresh, fresh, fresh, fresh, fresh])
    bridge = _Bridge()
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    result = restart_fresh_unseeded_run(
        runner,
        "RED",
        "WHITE",
        timeout_seconds=0.2,
        poll_interval_seconds=0,
    )

    assert result.before.sequence == 651
    assert result.after.sequence == 1
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


def test_restart_accepts_sticky_won_bit_on_authoritative_game_over():
    before = _snapshot(10, "GAME_OVER", won=True)
    fresh = _snapshot(11, "BLIND_SELECT")
    observer = _Observer([before, fresh, fresh, fresh, fresh, fresh, fresh])
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
    assert result.after is fresh
    assert bridge.status_calls == 1
    assert bridge.restart_calls == 1


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


def test_restart_fails_closed_if_unlock_drain_capability_is_missing():
    observer = _Observer([_snapshot(10, "GAME_OVER")])
    bridge = _Bridge(restart_unlock_drain="0")
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="unlock-confirmation draining"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=0.1,
            poll_interval_seconds=0,
        )

    assert bridge.restart_calls == 0


def test_restart_fails_closed_if_pause_release_capability_is_missing():
    observer = _Observer([_snapshot(10, "GAME_OVER")])
    bridge = _Bridge(restart_pause_release="0")
    runner = SimpleNamespace(observer=observer, bridge=bridge)

    with pytest.raises(LiveRunRestartError, match="pause release"):
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


def test_restart_bridge_triggers_and_drains_native_unlock_queue_before_setup():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert "bridge_revision=7" in source
    assert ";restart_unlock_drain=1" in source
    assert ";restart_pause_release=1" in source
    assert 'config.button == "continue_unlock"' in source
    assert 'type(unlock_notify) ~= "function"' in source
    assert "pcall(unlock_notify)" in source
    assert "unlock_queue_size() > 0" in source
    assert "pump_unlock_events()" in source
    assert "pcall(callback)" in source
    assert "G.SETTINGS.paused = false" in source
    assert "unlock confirmation drain exceeded safety limit" in source

    restart_body = source[source.index("local function execute_restart_run()") :]
    assert restart_body.index("drain_unlock_confirmations()") < restart_body.index(
        "G.FUNCS and G.FUNCS.start_setup_run"
    )
    assert restart_body.index("pcall(callback)") < restart_body.index(
        "G.SETTINGS.paused = false"
    )
