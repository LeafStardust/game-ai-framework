from types import SimpleNamespace

import pytest

from games.balatro.actions import BalatroAction
from games.balatro.live.external.live_memory_autonomous_loop_injected import (
    AutonomousLoopGuardError,
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousBridgeCapabilityError,
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


class _GameOverRunner(_FakeRunner):
    def __init__(self, phases, *, won):
        super().__init__(phases)
        self.won = bool(won)

    def execute(self, decision):
        result, status = super().execute(decision)
        if self.index >= len(self.phases):
            result = SimpleNamespace(
                after=LiveBalatroSnapshot(
                    sequence=self.sequence,
                    phase="GAME_OVER",
                    state_complete=True,
                    payload={"step": self.index, "won": self.won},
                )
            )
        return result, status


class _RoundEvalWinRunner(_FakeRunner):
    def execute(self, decision):
        result, status = super().execute(decision)
        result = SimpleNamespace(
            after=LiveBalatroSnapshot(
                sequence=self.sequence,
                phase="ROUND_EVAL",
                state_complete=True,
                payload={"step": self.index, "won": True},
            )
        )
        return result, status


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


def test_unbounded_execute_runs_until_authoritative_game_over():
    runner = _GameOverRunner(
        ["SELECTING_HAND", "ROUND_EVAL", "SHOP"],
        won=True,
    )
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=None)

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 3
    assert result.stop_reason == "game over (won)"
    assert result.steps[-1].after_phase == "GAME_OVER"
    assert runner.execute_calls == 3


def test_unbounded_execute_stops_on_win_bit_before_endless_cash_out():
    runner = _RoundEvalWinRunner(["SELECTING_HAND"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=None)

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 1
    assert result.stop_reason == "game over (won)"
    assert result.steps[-1].after_phase == "ROUND_EVAL"
    assert runner.execute_calls == 1


def test_execute_does_not_act_when_start_snapshot_already_has_win_bit():
    runner = _FakeRunner(["ROUND_EVAL"])

    original_decide = runner.decide

    def decide_won():
        decision = original_decide()
        return AutonomousStepDecision(
            snapshot=LiveBalatroSnapshot(
                sequence=decision.snapshot.sequence,
                phase=decision.snapshot.phase,
                state_complete=True,
                payload={"step": 0, "won": True},
            ),
            state=decision.state,
            action=decision.action,
            source=decision.source,
            notes=decision.notes,
        )

    runner.decide = decide_won
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=None)

    result = loop.execute(expected_start_phase="ROUND_EVAL")

    assert result.stop_reason == "game over (won)"
    assert result.steps == ()
    assert runner.execute_calls == 0


def test_stop_request_arriving_during_planning_cancels_before_execution():
    runner = _FakeRunner(["SELECTING_HAND"])
    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=None,
        stop_requested=lambda: runner.decide_calls >= 1,
    )

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert result.stop_reason == "stop requested"
    assert result.steps == ()
    assert runner.decide_calls == 1
    assert runner.execute_calls == 0
    assert runner.events == ["decide"]


def test_successful_transition_hook_runs_after_authoritative_postcondition():
    runner = _GameOverRunner(["SELECTING_HAND"], won=False)
    transitions = []

    def on_transition(decision, result, status):
        transitions.append(
            (
                decision.snapshot.phase,
                result.after.phase,
                status["achievement_gate"],
                runner.execute_calls,
            )
        )

    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=None,
        on_transition=on_transition,
    )

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert result.stop_reason == "game over (lost)"
    assert transitions == [("SELECTING_HAND", "GAME_OVER", "ENABLED", 1)]


def test_transition_hook_failure_stops_after_already_executed_action():
    runner = _FakeRunner(["SELECTING_HAND", "SHOP"])

    def fail_transition(*_args):
        raise RuntimeError("disk full")

    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=None,
        on_transition=fail_transition,
    )

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 1
    assert result.stop_reason == (
        "transition hook failed after executed action: disk full"
    )
    assert runner.execute_calls == 1
    assert runner.events == ["decide", "execute"]


class _CapabilityBlockedRunner(_FakeRunner):
    def execute(self, decision):
        self.events.append("execute")
        self.execute_calls += 1
        raise AutonomousBridgeCapabilityError(
            "installed first-party bridge does not advertise SKIP_BLIND support"
        )


def test_bridge_capability_block_stops_cleanly_without_crashing_supervisor_loop():
    runner = _CapabilityBlockedRunner(["BLIND_SELECT"])
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=None)

    result = loop.execute(expected_start_phase="BLIND_SELECT")

    assert result.steps == ()
    assert result.stop_reason.startswith("bridge capability blocked:")
    assert "SKIP_BLIND" in result.stop_reason
    assert runner.decide_calls == 1
    assert runner.execute_calls == 1
    assert runner.events == ["decide", "execute"]


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
