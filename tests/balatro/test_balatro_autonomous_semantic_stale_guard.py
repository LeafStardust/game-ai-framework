from games.balatro.live.external.live_memory_autonomous_step_injected import (
    _same_snapshot,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, payload):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SELECTING_HAND",
        state_complete=True,
        payload=payload,
    )


def test_autonomous_stale_guard_ignores_ui_only_drift_and_sequence_change():
    expected = _snapshot(
        10,
        {
            "money": 5,
            "hand": {
                "cards": [
                    {
                        "live_id": 101,
                        "value": {"rank": "A", "suit": "Spades"},
                        "ui": {"x": 1.0, "y": 2.0, "r": 0.0},
                    }
                ]
            },
        },
    )
    current = _snapshot(
        12,
        {
            "money": 5,
            "hand": {
                "cards": [
                    {
                        "live_id": 101,
                        "value": {"rank": "A", "suit": "Spades"},
                        "ui": {"x": 1.04, "y": 1.98, "r": 0.01},
                    }
                ]
            },
        },
    )

    assert _same_snapshot(expected, current) is True


def test_autonomous_stale_guard_still_blocks_gameplay_state_change():
    expected = _snapshot(
        20,
        {
            "money": 5,
            "hand": {"cards": [{"live_id": 101, "ui": {"x": 1.0}}]},
        },
    )
    current = _snapshot(
        21,
        {
            "money": 6,
            "hand": {"cards": [{"live_id": 101, "ui": {"x": 1.0}}]},
        },
    )

    assert _same_snapshot(expected, current) is False
