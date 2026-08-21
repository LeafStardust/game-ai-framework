from pathlib import Path


def test_windows_live_monitor_waits_for_user_after_monitor_process_exits():
    launcher = Path("BalatroAgentMonitor.bat").read_text(encoding="utf-8")

    assert "balatro_agent_monitor_targets" in launcher
    assert "pause >nul" in launcher.lower()
    assert "press any key to close" in launcher.lower()
