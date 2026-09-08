from __future__ import annotations

from types import SimpleNamespace

import pytest

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_loop_injected import (
    AutonomousLoopGuardError,
    LiveMemoryInjectedAutonomousLoop,
)


class _ChangingObserver:
    def __init__(self, *, state_complete: bool):
        self.state_complete = bool(state_complete)
        self.sequence = 0

    def observe(self):
        self.sequence += 1
        return LiveBalatroSnapshot(
            sequence=self.sequence,
            phase="TAROT_PACK",
            state_complete=self.state_complete,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": False,
                # Deliberately changes every observation to model a native pack/UI
                # animation that remains publicly complete but not yet semantically
                # identical across adjacent memory snapshots.
                "animation_public_counter": self.sequence,
            },
        )


def _loop(observer):
    runner = SimpleNamespace(observer=observer)
    return LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=1,
        stability_interval_seconds=0.0,
        stability_timeout_seconds=0.001,
    )


def test_complete_pack_animation_timeout_returns_latest_safe_checkpoint():
    observer = _ChangingObserver(state_complete=True)

    checkpoint = _loop(observer)._wait_for_stable_checkpoint()

    assert checkpoint is not None
    assert checkpoint.phase == "TAROT_PACK"
    assert checkpoint.state_complete is True
    assert checkpoint.sequence >= 1


def test_incomplete_animation_timeout_still_fails_closed():
    observer = _ChangingObserver(state_complete=False)

    with pytest.raises(
        AutonomousLoopGuardError,
        match="live public state remained incomplete before planning",
    ):
        _loop(observer)._wait_for_stable_checkpoint()
