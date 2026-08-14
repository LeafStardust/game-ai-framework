from types import SimpleNamespace

from games.balatro.live.external.agent_control import BalatroAgentControl
from games.balatro.live.external.balatro_agent_supervisor import BalatroAgentSupervisor
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Runner:
    def __init__(self):
        self.decision = AutonomousStepDecision(
            snapshot=LiveBalatroSnapshot(
                sequence=10,
                phase="SELECTING_HAND",
                state_complete=True,
                payload={},
            ),
            state=SimpleNamespace(hand=()),
            action=SimpleNamespace(name="TEST_ACTION", cards=(), target=None),
            source="test policy",
            notes=("candidate A beats candidate B",),
        )

    def decide(self):
        return self.decision

    def execute(self, decision):
        assert decision is self.decision
        return (
            SimpleNamespace(
                after=LiveBalatroSnapshot(
                    sequence=11,
                    phase="SHOP",
                    state_complete=True,
                    payload={},
                )
            ),
            {"bridge": "1", "achievement_gate": "ENABLED"},
        )


def test_instrumented_runner_publishes_decision_and_execution_activity(tmp_path):
    control = BalatroAgentControl(tmp_path / "control")
    supervisor = BalatroAgentSupervisor(
        control=control,
        session_directory=tmp_path / "sessions",
        run_log_directory=tmp_path / "runs",
        session_id="session-test",
    )
    runner = supervisor._instrument_runner(
        _Runner(),
        attempt_number=2,
        run_id="session-test-attempt-002",
        deck="RED",
        stake="WHITE",
    )

    decision = runner.decide()
    telemetry = control.read_telemetry()
    assert telemetry["activity"] == "DECIDED"
    assert telemetry["attempt"] == 2
    assert telemetry["run_id"] == "session-test-attempt-002"
    assert telemetry["phase"] == "SELECTING_HAND"
    assert telemetry["action"] == "TEST_ACTION"
    assert telemetry["decision_source"] == "test policy"
    assert telemetry["notes"] == ["candidate A beats candidate B"]

    result, _ = runner.execute(decision)
    telemetry = control.read_telemetry()
    assert result.after.phase == "SHOP"
    assert telemetry["activity"] == "SETTLED"
    assert telemetry["phase"] == "SHOP"
    assert telemetry["checkpoint_sequence"] == 11
    assert telemetry["action"] == "TEST_ACTION"
