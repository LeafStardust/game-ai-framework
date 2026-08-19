from types import SimpleNamespace

from games.balatro.actions import BalatroAction
from games.balatro.live.external.live_memory_autonomous_loop_injected import (
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    AutonomousStepGuardError,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence: int, *, score: int, phase: str = "ROUND_EVAL"):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"score": score},
    )


class _SequenceObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)
        self.last = snapshots[-1]
        self.calls = 0

    def observe(self):
        self.calls += 1
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class _StableDecisionRunner:
    def __init__(self, observer):
        self.observer = observer
        self.decide_calls = 0
        self.execute_calls = 0
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def decide(self):
        self.decide_calls += 1
        snapshot = self.observer.observe()
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(hand=()),
            action=BalatroAction("END_ROUND"),
            source="test policy",
        )

    def execute(self, decision):
        self.execute_calls += 1
        after = _snapshot(
            decision.snapshot.sequence + 1,
            score=int(decision.snapshot.payload["score"]),
            phase="SHOP",
        )
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_preplan_stability_waits_for_semantic_score_to_stop_changing():
    observer = _SequenceObserver(
        _snapshot(1, score=648),
        _snapshot(2, score=359),
        _snapshot(2, score=359),
    )
    runner = _StableDecisionRunner(observer)
    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=1,
        stability_interval_seconds=0.0,
        stability_timeout_seconds=0.5,
    )

    stable = loop._wait_for_stable_checkpoint()

    assert stable.payload["score"] == 359
    assert observer.calls == 3
    assert runner.decide_calls == 0
    assert runner.execute_calls == 0


class _OneStaleRunner(_StableDecisionRunner):
    def execute(self, decision):
        self.execute_calls += 1
        if self.execute_calls == 1:
            raise AutonomousStepGuardError(
                "live state changed after autonomous planning; "
                "decide again from the new checkpoint"
            )
        after = _snapshot(
            decision.snapshot.sequence + 1,
            score=int(decision.snapshot.payload["score"]),
            phase="SHOP",
        )
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_stale_replan_does_not_consume_gameplay_step():
    stable = _snapshot(10, score=359)
    observer = _SequenceObserver(stable)
    runner = _OneStaleRunner(observer)
    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=1,
        stale_replan_limit=3,
        stability_interval_seconds=0.0,
        stability_timeout_seconds=0.5,
    )

    result = loop.execute(expected_start_phase="ROUND_EVAL")

    assert len(result.steps) == 1
    assert result.steps[0].number == 1
    assert result.steps[0].stale_replans == 1
    assert runner.decide_calls == 2
    assert runner.execute_calls == 2
    assert result.stop_reason == "max steps reached"
