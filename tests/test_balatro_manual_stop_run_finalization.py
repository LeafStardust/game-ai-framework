import json
from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.agent_control import BalatroAgentControl
from games.balatro.live.runtime.balatro_agent_supervisor import BalatroAgentSupervisor
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
)


class _Observer:
    def __init__(self):
        self.after_action = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def observe(self):
        sequence = 2 if self.after_action else 1
        return LiveBalatroSnapshot(
            sequence=sequence,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": False,
                "hand": {"cards": []},
                "marker": sequence,
            },
        )


class _StopAfterOneActionRunner:
    def __init__(self, observer, control):
        self.observer = observer
        self.control = control
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def decide(self):
        snapshot = self.observer.observe()
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(
                deck_name="RED",
                stake_name="WHITE",
                hand=(),
            ),
            action=BalatroAction(PLAY_CARDS),
            source="test D1",
            notes=("mode=TEST",),
        )

    def execute(self, decision):
        assert decision.snapshot.sequence == 1
        self.observer.after_action = True
        after = self.observer.observe()
        self.control.request_stop()
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_manual_stop_finalizes_active_run_and_session_artifacts(tmp_path):
    control = BalatroAgentControl(tmp_path / "control")
    observer = _Observer()
    run_directory = tmp_path / "runs"
    session_directory = tmp_path / "sessions"
    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=lambda: observer,
        runner_factory=lambda current: _StopAfterOneActionRunner(current, control),
        run_log_directory=run_directory,
        session_directory=session_directory,
        session_id="manual-stop-release",
        startup_stability_interval_seconds=0.0,
    )

    result = supervisor.run()

    assert result.won is False
    assert result.stop_reason == "manual stop requested"
    assert len(result.attempts) == 1
    attempt = result.attempts[0]
    assert attempt.outcome == "STOPPED"
    assert attempt.stop_reason == "stop requested"
    assert attempt.actions == 1
    assert control.read_status()["state"] == "OFF"

    run_path = run_directory / f"{attempt.run_id}.jsonl"
    run_summary_path = run_directory / f"{attempt.run_id}.summary.json"
    assert run_path.exists()
    assert run_summary_path.exists()
    assert result.summary_path.exists()

    rows = [
        json.loads(line)
        for line in run_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[-1]["event"] == "run_finished"
    assert rows[-1]["data"]["won"] is False
    assert rows[-1]["data"]["reason"] == "stop requested"
    assert rows[-1]["data"]["state"]["phase"] == "SELECTING_HAND"

    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    assert run_summary["reason"] == "stop requested"
    assert run_summary["won"] is False
    assert run_summary["last_sequence"] == rows[-1]["sequence"]
    assert run_summary["event_count"] == len(rows)

    session_summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert session_summary["attempt_count"] == 1
    assert session_summary["attempts"][0]["outcome"] == "STOPPED"
    assert session_summary["stop_reason"] == "manual stop requested"
