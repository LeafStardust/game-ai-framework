import time

from games.balatro.live.external.balatro_agent_supervisor import (
    wait_for_stable_startup_snapshot,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _ColdAttachObserver:
    def __init__(self):
        self.calls = 0

    def observe(self):
        self.calls += 1
        if self.calls == 1:
            # Simulate cold process attachment / G discovery taking longer than
            # the semantic stability timeout. This connection cost must not be
            # treated as failure of the already-running game state to settle.
            time.sleep(0.02)
        return LiveBalatroSnapshot(
            sequence=1,
            phase="BLIND_SELECT",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": False,
                "hand": {"cards": []},
            },
        )


def test_startup_stability_timeout_begins_after_cold_first_observation():
    observer = _ColdAttachObserver()

    snapshot = wait_for_stable_startup_snapshot(
        observer,
        interval_seconds=0.0,
        timeout_seconds=0.001,
    )

    assert observer.calls == 2
    assert snapshot.phase == "BLIND_SELECT"
    assert snapshot.payload["deck"] == "RED"
    assert snapshot.payload["stake"] == "WHITE"
