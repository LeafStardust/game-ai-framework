from types import SimpleNamespace

import pytest

from games.balatro.actions import BalatroAction
from games.balatro.live.external.live_memory_autonomous_loop_injected import (
    AutonomousLoopGuardError,
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    UnsupportedAutonomousPhase,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _FakeRunner:
    def __init__(self, phases):
        self.phases = tuple(phases)
        self.index = 0
        self.sequence = 1
        self.decide_calls = 0
        self.execute_calls = 0
        self.events = []
        self.last_observation_seconds = 0.01
        self.last_translation_seconds = 0.02
        self.last_policy_seconds = 0.03

    def decide(self):
        self.events.append("decide")
        self.decide_calls += 1
        if self.index >= len(self.phases):
            raise UnsupportedAutonomousPhase("test terminal phase")
        phase = self.phases[self.index]
        snapshot = LiveBalatroSnapshot(
            sequence=self.sequence,
            phase=phase,
            state_complete=True,
            payload={"step": self.index},
        )
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(hand=()),
            action=BalatroAction(f"ACTION_{self.index}"),
            source="test policy",
            notes=(f"decision={self.index}",),
        )

    def execute(self, decision):
        self.events.append("execute")
        self.execute_calls += 1
        assert decision.snapshot.sequence == self.sequence
        assert decision.snapshot.phase == self.phases[self.index]
        self.sequence += 1
        self.index += 1
        after_phase = (
            self.phases[self.index]
            if self.index < len(self.phases)
            else "TERMINAL"
        )
        after = LiveBalatroSnapshot(
            sequence=self.sequence,
            phase=after_phase,
            state_complete=True,
            payload={"step": self.index},
        )
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_preview_decides_once_without_executing():
    runner = _FakeRunner(["SELECTING_HAND"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=5)

    step = loop.preview()

    assert step.number == 1
    assert step.decision.snapshot.phase == "SELECTING_HAND"
    assert step.after_phase is None
    assert runner.decide_calls == 1
    assert runner.execute_calls == 0
    assert runner.events == ["decide"]


def test_execute_redecides_after_every_settled_checkpoint():
    runner = _FakeRunner(
        ["SELECTING_HAND", "SELECTING_HAND", "ROUND_EVAL", "SHOP"]
    )
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=3)

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 3
    assert result.stop_reason == "max steps reached"
    assert [step.decision.snapshot.phase for step in result.steps] == [
        "SELECTING_HAND",
        "SELECTING_HAND",
        "ROUND_EVAL",
    ]
    assert [step.after_phase for step in result.steps] == [
        "SELECTING_HAND",
        "ROUND_EVAL",
        "SHOP",
    ]
    assert [step.after_sequence for step in result.steps] == [2, 3, 4]
    assert all(step.achievement_gate == "ENABLED" for step in result.steps)
    assert runner.events == [
        "decide",
        "execute",
        "decide",
        "execute",
        "decide",
        "execute",
    ]


def test_execute_blocks_wrong_start_phase_before_gameplay_action():
    runner = _FakeRunner(["SHOP"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=2)

    with pytest.raises(AutonomousLoopGuardError, match="expected start phase"):
        loop.execute(expected_start_phase="SELECTING_HAND")

    assert runner.decide_calls == 1
    assert runner.execute_calls == 0


def test_execute_stops_cleanly_when_next_phase_is_unsupported():
    runner = _FakeRunner(["SELECTING_HAND"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=4)

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 1
    assert result.steps[0].after_phase == "TERMINAL"
    assert result.stop_reason.startswith("unsupported phase:")
    assert runner.decide_calls == 2
    assert runner.execute_calls == 1


class _NonAdvancingRunner(_FakeRunner):
    def execute(self, decision):
        self.events.append("execute")
        self.execute_calls += 1
        after = LiveBalatroSnapshot(
            sequence=decision.snapshot.sequence,
            phase=decision.snapshot.phase,
            state_complete=True,
            payload=decision.snapshot.payload,
        )
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_execute_fails_closed_if_action_does_not_advance_checkpoint():
    runner = _NonAdvancingRunner(["SELECTING_HAND"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=1)

    with pytest.raises(AutonomousLoopGuardError, match="did not advance"):
        loop.execute(expected_start_phase="SELECTING_HAND")
