import json
from types import SimpleNamespace

from games.balatro.actions import BalatroAction
from games.balatro.live.runtime import agent_control as agent_control_module
from games.balatro.live.runtime import balatro_agent_supervisor as supervisor_module
from games.balatro.live.runtime import balatro_agent_toggle as toggle_module
from games.balatro.live.runtime.agent_control import BalatroAgentControl
from games.balatro.live.runtime.balatro_agent_supervisor import (
    BalatroAgentSupervisor,
    wait_for_stable_startup_snapshot,
)
from games.balatro.live.runtime.balatro_agent_toggle import toggle_agent
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
)
from games.balatro.live.runtime.live_memory_restart_run_injected import (
    LiveRunRestartError,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _FakeAttemptObserver:
    def __init__(self, *, won):
        self.won = bool(won)
        self.index = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def observe(self):
        if self.index == 0:
            return LiveBalatroSnapshot(
                sequence=1,
                phase="SELECTING_HAND",
                state_complete=True,
                payload={
                    "deck": "RED",
                    "stake": "WHITE",
                    "won": False,
                    "hand": {"cards": []},
                },
            )
        return LiveBalatroSnapshot(
            sequence=2,
            phase="GAME_OVER",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": self.won,
                "hand": {"cards": []},
            },
        )


class _FakeAttemptRunner:
    def __init__(self, observer):
        self.observer = observer
        self.last_observation_seconds = 0.01
        self.last_translation_seconds = 0.02
        self.last_policy_seconds = 0.03

    def decide(self):
        snapshot = self.observer.observe()
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(
                deck_name="RED",
                stake_name="WHITE",
                hand=(),
            ),
            action=BalatroAction("PLAY_CARDS"),
            source="test D1",
            notes=("mode=TEST",),
        )

    def execute(self, decision):
        assert decision.snapshot.phase == "SELECTING_HAND"
        self.observer.index = 1
        return SimpleNamespace(after=self.observer.observe()), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


class _AttemptFactory:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.index = 0
        self.restart_calls = []

    def observer(self):
        return _FakeAttemptObserver(won=self.outcomes[self.index])

    def restart(self, _runner, deck, stake):
        self.restart_calls.append((deck, stake))
        self.index += 1


class _TransientStartupObserver:
    def __init__(self):
        self.calls = 0

    def observe(self):
        self.calls += 1
        if self.calls == 1:
            return LiveBalatroSnapshot(
                sequence=1,
                phase="UNKNOWN",
                state_complete=False,
                payload={"deck": "BLUE", "stake": "WHITE"},
            )
        return LiveBalatroSnapshot(
            sequence=2,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "hand": {"cards": []},
            },
        )


def test_stable_startup_snapshot_ignores_transient_first_attachment_frame():
    observer = _TransientStartupObserver()

    stable = wait_for_stable_startup_snapshot(
        observer,
        interval_seconds=0.0,
        timeout_seconds=0.1,
    )

    assert observer.calls == 3
    assert stable.phase == "SELECTING_HAND"
    assert stable.state_complete is True
    assert stable.payload["deck"] == "RED"
    assert stable.payload["stake"] == "WHITE"


def test_supervisor_retries_fresh_attempts_until_win_and_auto_off(tmp_path):
    factory = _AttemptFactory([False, True])
    control = BalatroAgentControl(tmp_path / "control")
    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=factory.observer,
        runner_factory=_FakeAttemptRunner,
        restart_run=factory.restart,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
        session_id="session-test",
        startup_stability_interval_seconds=0.0,
    )

    result = supervisor.run()

    assert result.won is True
    assert result.stop_reason == "target run won; auto-off"
    assert [attempt.outcome for attempt in result.attempts] == ["LOSS", "WIN"]
    assert [attempt.run_id for attempt in result.attempts] == [
        "session-test-attempt-001",
        "session-test-attempt-002",
    ]
    assert all(attempt.playbook == "red-white" for attempt in result.attempts)
    assert all(attempt.playbook_version == "0.8" for attempt in result.attempts)
    assert factory.restart_calls == [("RED", "WHITE")]
    assert control.running_pid() is None
    assert control.read_status()["state"] == "OFF"

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["attempt_count"] == 2
    assert summary["loss_count"] == 1
    assert summary["won"] is True
    assert summary["target_deck"] == "RED"
    assert summary["target_stake"] == "WHITE"

    for attempt in result.attempts:
        path = tmp_path / "runs" / f"{attempt.run_id}.jsonl"
        attempt_summary = tmp_path / "runs" / f"{attempt.run_id}.summary.json"
        assert path.exists()
        assert attempt_summary.exists()


def test_supervisor_defaults_to_validated_native_loss_restart(tmp_path):
    supervisor = BalatroAgentSupervisor(
        control=BalatroAgentControl(tmp_path / "control"),
        session_id="native-restart-default",
    )

    assert supervisor.restart_run is supervisor_module.restart_fresh_unseeded_run


def test_supervisor_fails_closed_when_native_restart_postcondition_fails(tmp_path):
    factory = _AttemptFactory([False])
    control = BalatroAgentControl(tmp_path / "control")

    def failed_restart(_runner, _deck, _stake):
        raise LiveRunRestartError("restart postcondition did not settle")

    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=factory.observer,
        runner_factory=_FakeAttemptRunner,
        restart_run=failed_restart,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
        session_id="restart-blocked",
        startup_stability_interval_seconds=0.0,
    )

    result = supervisor.run()

    assert result.won is False
    assert len(result.attempts) == 1
    assert result.attempts[0].outcome == "LOSS"
    assert result.stop_reason.startswith("RESTART_FAILED:")
    assert control.read_status()["state"] == "OFF"


def test_toggle_launches_once_then_requests_cooperative_stop(tmp_path, monkeypatch):
    control = BalatroAgentControl(tmp_path / "control")

    class _Process:
        pid = 4242

    monkeypatch.setattr(
        toggle_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _Process(),
    )
    monkeypatch.setattr(toggle_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        agent_control_module,
        "_process_is_running",
        lambda pid: pid == 4242,
    )

    state, pid = toggle_agent(control, session_id="toggle-test")

    assert state == "STARTING"
    assert pid == 4242
    assert control.read_pid() == 4242
    assert control.stop_requested() is False
    assert control.read_status()["state"] == "STARTING"

    state, pid = toggle_agent(control)

    assert state == "STOPPING"
    assert pid == 4242
    assert control.stop_requested() is True
    status = control.read_status()
    assert status["state"] == "STOPPING"
    assert "before the next gameplay action" in status["reason"]
