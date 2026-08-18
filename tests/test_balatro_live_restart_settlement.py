import pytest

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.balatro_agent_supervisor import (
    POST_RESTART_REJECTED_STARTUP_PHASES,
    wait_for_stable_startup_snapshot,
)
from games.balatro.live.runtime.live_memory_restart_run_injected import (
    LiveRunRestartError,
    restart_fresh_unseeded_run,
)


class _SequenceObserver:
    def __init__(self, snapshots):
        self._snapshots = iter(snapshots)

    def observe(self):
        return next(self._snapshots)


class _RestartBridge:
    def __init__(self):
        self.restart_calls = 0

    def status(self):
        return {
            "restart_run_callback": "START_RUN_PRESENT",
            "restart_unlock_drain": "1",
        }

    def restart_run(self):
        self.restart_calls += 1


class _Runner:
    def __init__(self, snapshots):
        self.observer = _SequenceObserver(snapshots)
        self.bridge = _RestartBridge()


def _snapshot(
    sequence,
    phase,
    *,
    complete=True,
    deck="RED",
    stake="WHITE",
    won=False,
    marker=None,
):
    payload = {
        "deck": deck,
        "stake": stake,
        "won": won,
    }
    if marker is not None:
        payload["marker"] = marker
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=complete,
        payload=payload,
    )


def test_restart_ignores_false_fresh_window_before_unlock_tail_resettles():
    before = _snapshot(10, "GAME_OVER")
    transient = _snapshot(11, "BLIND_SELECT", marker="transient")
    unlock_tail = _snapshot(12, "GAME_OVER", marker="unlock-tail")
    settled = _snapshot(13, "BLIND_SELECT", marker="settled")
    runner = _Runner(
        [
            before,
            transient,
            transient,
            unlock_tail,
            settled,
            settled,
            settled,
        ]
    )

    result = restart_fresh_unseeded_run(
        runner,
        "RED",
        "WHITE",
        timeout_seconds=1.0,
        poll_interval_seconds=0.0,
        stable_confirmations=3,
    )

    assert result.before is before
    assert result.after is settled
    assert result.after.payload["marker"] == "settled"
    assert runner.bridge.restart_calls == 1


def test_restart_stability_counter_resets_on_incomplete_unlock_frame():
    before = _snapshot(20, "GAME_OVER")
    fresh = _snapshot(21, "BLIND_SELECT", marker="fresh")
    incomplete = _snapshot(
        22,
        "BLIND_SELECT",
        complete=False,
        marker="unlock-transition",
    )
    settled = _snapshot(23, "BLIND_SELECT", marker="settled")
    runner = _Runner(
        [
            before,
            fresh,
            fresh,
            incomplete,
            settled,
            settled,
            settled,
        ]
    )

    result = restart_fresh_unseeded_run(
        runner,
        "RED",
        "WHITE",
        timeout_seconds=1.0,
        poll_interval_seconds=0.0,
        stable_confirmations=3,
    )

    assert result.after is settled
    assert runner.bridge.restart_calls == 1


def test_retry_attachment_ignores_stable_terminal_unlock_tail():
    stale_game_over = _snapshot(50, "GAME_OVER", marker="unlock-tail")
    fresh = _snapshot(51, "BLIND_SELECT", marker="fresh-run")
    observer = _SequenceObserver(
        [
            stale_game_over,
            stale_game_over,
            fresh,
            fresh,
        ]
    )

    result = wait_for_stable_startup_snapshot(
        observer,
        interval_seconds=0.0,
        timeout_seconds=1.0,
        rejected_phases=POST_RESTART_REJECTED_STARTUP_PHASES,
    )

    assert result.phase == "BLIND_SELECT"
    assert result.payload["marker"] == "fresh-run"


def test_restart_rejects_identity_change_at_fresh_checkpoint():
    before = _snapshot(30, "GAME_OVER")
    wrong_identity = _snapshot(31, "BLIND_SELECT", deck="BLUE")
    runner = _Runner([before, wrong_identity])

    with pytest.raises(LiveRunRestartError, match="changed deck/stake"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=1.0,
            poll_interval_seconds=0.0,
            stable_confirmations=3,
        )

    assert runner.bridge.restart_calls == 1


def test_restart_requires_multiple_stable_confirmations():
    runner = _Runner([_snapshot(40, "GAME_OVER")])

    with pytest.raises(ValueError, match="stable_confirmations must be at least 2"):
        restart_fresh_unseeded_run(
            runner,
            "RED",
            "WHITE",
            timeout_seconds=1.0,
            poll_interval_seconds=0.0,
            stable_confirmations=1,
        )

    assert runner.bridge.restart_calls == 0
