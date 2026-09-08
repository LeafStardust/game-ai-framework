from games.balatro.live.runtime import agent_control as control_module
from games.balatro.live.runtime import balatro_agent_monitor as monitor
from games.balatro.live.runtime import balatro_agent_toggle as toggle
from games.balatro.live.runtime.agent_control import BalatroAgentControl


def test_live_monitor_is_persistent_by_default():
    assert monitor.DEFAULT_FINAL_HOLD_SECONDS is None

    dashboard = monitor.build_dashboard(
        {"state": "OFF"},
        supervisor_pid=None,
        balatro_running=True,
        rows=[],
    )

    assert "stays open while the agent is OFF" in dashboard
    assert "resumes on its next start" in dashboard


def test_toggle_reuses_running_monitor_instead_of_spawning_duplicate(
    tmp_path,
    monkeypatch,
):
    control = BalatroAgentControl(tmp_path / "control")
    control.claim_monitor_process(pid=1234)
    monkeypatch.setattr(control_module, "_process_is_running", lambda pid: pid == 1234)
    spawned = []
    monkeypatch.setattr(toggle.subprocess, "Popen", lambda *args, **kwargs: spawned.append((args, kwargs)))

    toggle.launch_monitor(control)

    assert spawned == []
    assert control.running_monitor_pid() == 1234


def test_stale_monitor_pid_is_cleared_before_relaunch(tmp_path, monkeypatch):
    control = BalatroAgentControl(tmp_path / "control")
    control.claim_monitor_process(pid=1234)
    monkeypatch.setattr(control_module, "_process_is_running", lambda pid: False)
    spawned = []
    monkeypatch.setattr(toggle.subprocess, "Popen", lambda *args, **kwargs: spawned.append((args, kwargs)))

    toggle.launch_monitor(control)

    assert len(spawned) == 1
    assert control.read_monitor_pid() is None
