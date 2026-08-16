import pytest

from games.balatro.live.runtime import agent_control as agent_control_module
from games.balatro.live.runtime import balatro_agent_toggle as toggle_module
from games.balatro.live.runtime.agent_control import BalatroAgentControl
from games.balatro.live.runtime.balatro_agent_toggle import hard_stop_agent


def _record_running_supervisor(
    control: BalatroAgentControl,
    pid: int,
    *,
    state: str = "ON",
    status_pid=None,
) -> None:
    control.ensure_directory()
    control.pid_path.write_text(str(pid), encoding="utf-8")
    control.write_status(
        state,
        pid=pid if status_pid is None else status_pid,
        session_id="hard-stop-session",
        attempt=3,
        run_id="hard-stop-session-attempt-003",
    )


def test_emergency_hard_stop_force_terminates_only_recorded_supervisor(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    _record_running_supervisor(control, 4242)
    running = {4242}
    terminated = []

    monkeypatch.setattr(
        agent_control_module,
        "_process_is_running",
        lambda pid: pid in running,
    )

    def terminate(pid):
        terminated.append(pid)
        running.discard(pid)

    monkeypatch.setattr(toggle_module, "_force_terminate_process", terminate)

    pid = hard_stop_agent(control)

    assert pid == 4242
    assert terminated == [4242]
    assert control.read_pid() is None
    assert control.stop_requested() is False
    status = control.read_status()
    assert status["state"] == "OFF"
    assert status["session_id"] == "hard-stop-session"
    assert status["attempt"] == 3
    assert status["run_id"] == "hard-stop-session-attempt-003"
    assert "supervisor force-terminated" in status["reason"]
    assert "Balatro left running" in status["reason"]


def test_emergency_hard_stop_refuses_conflicting_status_pid(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    _record_running_supervisor(control, 4242, status_pid=9999)
    monkeypatch.setattr(
        agent_control_module,
        "_process_is_running",
        lambda pid: pid == 4242,
    )
    terminated = []
    monkeypatch.setattr(
        toggle_module,
        "_force_terminate_process",
        lambda pid: terminated.append(pid),
    )

    with pytest.raises(RuntimeError, match="does not match agent.pid"):
        hard_stop_agent(control)

    assert terminated == []
    assert control.read_pid() == 4242


def test_emergency_hard_stop_refuses_explicit_off_status(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    _record_running_supervisor(control, 4242, state="OFF")
    monkeypatch.setattr(
        agent_control_module,
        "_process_is_running",
        lambda pid: pid == 4242,
    )
    terminated = []
    monkeypatch.setattr(
        toggle_module,
        "_force_terminate_process",
        lambda pid: terminated.append(pid),
    )

    with pytest.raises(RuntimeError, match="status says OFF"):
        hard_stop_agent(control)

    assert terminated == []
    assert control.read_pid() == 4242


def test_emergency_hard_stop_preserves_control_state_when_termination_fails(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    _record_running_supervisor(control, 4242)
    monkeypatch.setattr(
        agent_control_module,
        "_process_is_running",
        lambda pid: pid == 4242,
    )

    def fail(_pid):
        raise OSError("access denied")

    monkeypatch.setattr(toggle_module, "_force_terminate_process", fail)

    with pytest.raises(OSError, match="access denied"):
        hard_stop_agent(control)

    assert control.read_pid() == 4242
    status = control.read_status()
    assert status["state"] == "HARD_STOP_FAILED"
    assert "access denied" in status["reason"]


def test_emergency_hard_stop_is_noop_when_supervisor_is_not_running(
    tmp_path,
):
    control = BalatroAgentControl(tmp_path / "control")

    assert hard_stop_agent(control) is None
