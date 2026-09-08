from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
    semantic_snapshot_key,
)


class _NonPollingObserver(DiscardHistorySupervisorLiveMemoryBalatroObserver):
    def __init__(self):
        pass

    def _observe_public(self):
        raise AssertionError("production general quiet hook must not poll")


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


def test_production_supervisor_general_quiet_hook_returns_without_polling():
    observer = _NonPollingObserver()
    snapshot = _snapshot(41, money=17, x=12.0)

    result = observer._wait_for_full_state_quiet(snapshot)

    assert result is snapshot


def test_general_quiet_hook_does_not_require_semantic_state_to_stop_changing():
    observer = _NonPollingObserver()
    initial = _snapshot(42, money=17)
    changed = _snapshot(43, money=18)

    assert semantic_snapshot_key(initial) != semantic_snapshot_key(changed)
    assert observer._wait_for_full_state_quiet(initial) is initial
    assert observer._wait_for_full_state_quiet(changed) is changed
