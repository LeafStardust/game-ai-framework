from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime import live_memory_discard_history_observer as observer_module
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
    semantic_snapshot_key,
)


class _Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += float(seconds)


class _QuietObserver(DiscardHistorySupervisorLiveMemoryBalatroObserver):
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.full_state_quiet_seconds = 1.0
        self.full_state_quiet_timeout_seconds = 5.0
        self.full_state_quiet_poll_seconds = 0.25
        self._last_semantic_quiescent_key = None
        self._last_quiescent_sequence = None

    def _observe_public(self):
        if self.snapshots:
            return self.snapshots.pop(0)
        raise AssertionError("semantic quiet gate polled beyond supplied snapshots")


def _snapshot(sequence, *, money=10, x=0.0):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={
            "money": money,
            "shop": {
                "jokers": {
                    "cards": [
                        {
                            "live_id": 1,
                            "center": "j_joker",
                            "label": "Joker",
                            "ui": {"x": x, "y": 0.0},
                        }
                    ]
                }
            },
        },
    )


def test_semantic_snapshot_key_ignores_ui_geometry_but_not_game_state():
    before = _snapshot(1, money=10, x=0.0)
    moved = _snapshot(2, money=10, x=12.0)
    changed = _snapshot(3, money=11, x=12.0)

    assert semantic_snapshot_key(before) == semantic_snapshot_key(moved)
    assert semantic_snapshot_key(before) != semantic_snapshot_key(changed)


def test_supervisor_quiet_gate_does_not_reset_on_ui_only_sequence_churn(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(observer_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(observer_module, "sleep", clock.sleep)

    initial = _snapshot(1, x=0.0)
    observer = _QuietObserver(
        [
            _snapshot(2, x=1.0),
            _snapshot(3, x=2.0),
            _snapshot(4, x=3.0),
            _snapshot(5, x=4.0),
        ]
    )

    result = observer._wait_for_full_state_quiet(initial)

    assert result.sequence == 5
    assert clock.now == 1.0
    assert observer._last_semantic_quiescent_key == semantic_snapshot_key(result)


def test_supervisor_quiet_gate_resets_on_semantic_public_change(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(observer_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(observer_module, "sleep", clock.sleep)

    initial = _snapshot(1, money=10)
    observer = _QuietObserver(
        [
            _snapshot(2, money=11),
            _snapshot(3, money=11, x=1.0),
            _snapshot(4, money=11, x=2.0),
            _snapshot(5, money=11, x=3.0),
            _snapshot(6, money=11, x=4.0),
        ]
    )

    result = observer._wait_for_full_state_quiet(initial)

    assert result.sequence == 6
    assert clock.now == 1.25
