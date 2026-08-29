from types import SimpleNamespace

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_loop_injected import (
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)
from games.balatro.live.runtime.round_eval_checkout_fastpath import (
    _READY_CAPABILITY_ATTR,
    _round_eval_ui_ready,
)


def _snapshot(phase: str, *, sequence: int = 1) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={},
    )


def test_round_eval_ui_readiness_requires_actual_round_eval_object():
    assert _round_eval_ui_ready({}) is False
    assert _round_eval_ui_ready({"round_eval": SimpleNamespace(kind="nil")}) is False
    assert _round_eval_ui_ready({"round_eval": SimpleNamespace(kind="table")}) is True
    assert _round_eval_ui_ready({"round_eval": SimpleNamespace(kind="userdata")}) is True


def test_round_eval_bypasses_generic_full_state_quiet_gate():
    observer = object.__new__(SupervisorLiveMemoryBalatroObserver)
    snapshot = _snapshot("ROUND_EVAL")

    result = observer._wait_for_full_state_quiet(snapshot)

    assert result is snapshot


class _CountingObserver:
    def __init__(self, snapshots, *, native_ready_capable: bool = False):
        self.snapshots = list(snapshots)
        self.calls = 0
        if native_ready_capable:
            setattr(self, _READY_CAPABILITY_ATTR, True)
            self._last_exposed_phase = str(self.snapshots[0].phase)

    def observe(self):
        self.calls += 1
        index = min(self.calls - 1, len(self.snapshots) - 1)
        snapshot = self.snapshots[index]
        if bool(getattr(self, _READY_CAPABILITY_ATTR, False)):
            self._last_exposed_phase = str(snapshot.phase)
        return snapshot


class _Runner:
    def __init__(self, observer):
        self.observer = observer


def test_round_eval_skips_two_snapshot_autonomous_stability_confirmation():
    observer = _CountingObserver(
        [_snapshot("ROUND_EVAL")],
        native_ready_capable=True,
    )
    loop = LiveMemoryInjectedAutonomousLoop(
        _Runner(observer),
        max_steps=1,
        stability_interval_seconds=10.0,
    )

    result = loop._wait_for_stable_checkpoint()

    assert result.phase == "ROUND_EVAL"
    assert observer.calls == 1


def test_non_round_eval_keeps_normal_two_snapshot_stability_confirmation():
    first = _snapshot("SHOP", sequence=1)
    observer = _CountingObserver([first, first], native_ready_capable=True)
    loop = LiveMemoryInjectedAutonomousLoop(
        _Runner(observer),
        max_steps=1,
        stability_interval_seconds=0.0,
    )

    result = loop._wait_for_stable_checkpoint()

    assert result.phase == "SHOP"
    assert observer.calls == 2


def test_round_eval_without_native_readiness_capability_keeps_normal_stability():
    first = _snapshot("ROUND_EVAL", sequence=1)
    observer = _CountingObserver([first, first])
    loop = LiveMemoryInjectedAutonomousLoop(
        _Runner(observer),
        max_steps=1,
        stability_interval_seconds=0.0,
    )

    result = loop._wait_for_stable_checkpoint()

    assert result.phase == "ROUND_EVAL"
    assert observer.calls == 2
