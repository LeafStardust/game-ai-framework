from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.external.live_memory_autonomous_loop_injected import (
    _stale_difference_details,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, payload):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SELECTING_HAND",
        state_complete=True,
        payload=payload,
    )


def _decision(snapshot):
    return AutonomousStepDecision(
        snapshot=snapshot,
        state=SimpleNamespace(hand=[]),
        action=BalatroAction(PLAY_CARDS),
        source="test",
    )


def test_loop_stale_diagnostics_ignore_ui_only_drift():
    before = _snapshot(
        1,
        {
            "money": 5,
            "hand": {
                "cards": [
                    {
                        "live_id": 101,
                        "value": {"rank": "A", "suit": "Spades"},
                        "ui": {"x": 1.0, "y": 2.0},
                    }
                ]
            },
        },
    )
    after = _snapshot(
        2,
        {
            "money": 5,
            "hand": {
                "cards": [
                    {
                        "live_id": 101,
                        "value": {"rank": "A", "suit": "Spades"},
                        "ui": {"x": 1.2, "y": 1.8},
                    }
                ]
            },
        },
    )

    assert _stale_difference_details(_decision(before), after) == ()


def test_loop_stale_diagnostics_report_gameplay_paths():
    before = _snapshot(
        10,
        {
            "money": 5,
            "hand": {"cards": [{"live_id": 101}]},
        },
    )
    after = _snapshot(
        11,
        {
            "money": 6,
            "hand": {"cards": [{"live_id": 202}]},
        },
    )

    details = _stale_difference_details(_decision(before), after)

    assert any("payload.money" in item and "5 -> 6" in item for item in details)
    assert any(
        "payload.hand.cards[0].live_id" in item and "101 -> 202" in item
        for item in details
    )
