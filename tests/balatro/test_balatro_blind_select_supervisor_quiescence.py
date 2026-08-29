from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)


def _snapshot(phase: str) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=1,
        phase=phase,
        state_complete=True,
        payload={},
    )


class _HarnessObserver(SupervisorLiveMemoryBalatroObserver):
    def __init__(self, snapshot: LiveBalatroSnapshot) -> None:
        self._snapshot = snapshot
        self._last_exposed_phase = None
        self.blind_select_readiness_timeout_seconds = 1.0
        self.blind_select_readiness_poll_seconds = 0.0
        self.shop_readiness_timeout_seconds = 1.0
        self.shop_readiness_poll_seconds = 0.0
        self.quiet_calls = 0

    def _observe_public(self):
        return self._snapshot

    def _wait_for_native_readiness(self, snapshot, **kwargs):
        del kwargs
        return snapshot

    def _wait_for_full_state_quiet(self, snapshot):
        self.quiet_calls += 1
        return snapshot


def test_native_ready_blind_select_skips_raw_sequence_quiescence_gate():
    observer = _HarnessObserver(_snapshot("BLIND_SELECT"))

    result = observer.observe()

    assert result.phase == "BLIND_SELECT"
    assert observer.quiet_calls == 0
    assert observer._last_exposed_phase == "BLIND_SELECT"


def test_shop_still_requires_raw_sequence_quiescence_gate():
    observer = _HarnessObserver(_snapshot("SHOP"))

    result = observer.observe()

    assert result.phase == "SHOP"
    assert observer.quiet_calls == 1
    assert observer._last_exposed_phase == "SHOP"
