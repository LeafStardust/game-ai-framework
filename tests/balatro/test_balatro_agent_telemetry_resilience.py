import json

from games.balatro.live.runtime import agent_control as agent_control_module
from games.balatro.live.runtime.agent_control import BalatroAgentControl


def test_telemetry_replace_retries_transient_permission_error(tmp_path, monkeypatch):
    control = BalatroAgentControl(tmp_path / "control")
    real_replace = agent_control_module.os.replace
    attempts = []

    def flaky_replace(source, destination):
        if destination == control.telemetry_path:
            attempts.append((source, destination))
            if len(attempts) < 3:
                raise PermissionError(5, "Access is denied")
        return real_replace(source, destination)

    monkeypatch.setattr(agent_control_module.os, "replace", flaky_replace)
    monkeypatch.setattr(agent_control_module, "sleep", lambda _seconds: None)

    control.write_telemetry("SETTLED", attempt=7)

    assert len(attempts) == 3
    assert control.read_telemetry()["activity"] == "SETTLED"
    assert control.read_telemetry()["attempt"] == 7
    assert not tuple(control.directory.glob("telemetry.json.*.tmp"))


def test_telemetry_replace_exhaustion_is_nonfatal_and_preserves_status(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    control.ensure_directory()
    previous = {
        "schema": agent_control_module.AGENT_TELEMETRY_SCHEMA,
        "activity": "SETTLED",
        "updated_at": "previous",
        "attempt": 7,
    }
    control.telemetry_path.write_text(json.dumps(previous), encoding="utf-8")
    real_replace = agent_control_module.os.replace
    telemetry_attempts = []

    def locked_telemetry_replace(source, destination):
        if destination == control.telemetry_path:
            telemetry_attempts.append((source, destination))
            raise PermissionError(5, "Access is denied")
        return real_replace(source, destination)

    monkeypatch.setattr(
        agent_control_module.os,
        "replace",
        locked_telemetry_replace,
    )
    monkeypatch.setattr(agent_control_module, "sleep", lambda _seconds: None)

    control.mark_off(reason="attempt limit reached", attempts=10)

    assert len(telemetry_attempts) == agent_control_module.TELEMETRY_REPLACE_ATTEMPTS
    assert control.read_telemetry() == previous
    status = control.read_status()
    assert status["state"] == "OFF"
    assert status["reason"] == "attempt limit reached"
    assert status["attempts"] == 10
    assert not tuple(control.directory.glob("telemetry.json.*.tmp"))
