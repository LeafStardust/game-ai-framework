from games.balatro.live.external.live_memory_restart_capability import (
    RESTART_CALLBACK_UNREPORTED,
    restart_callback_state,
)
from games.balatro.live.injected.bridge import parse_status_message
from games.balatro.live.injected.install import bridge_asset_path


def test_extended_bridge_status_reports_restart_callback_presence():
    status = parse_status_message(
        "bridge=1;achievement_gate=ENABLED;"
        "restart_run_callback=START_RUN_PRESENT"
    )

    assert status["bridge"] == "1"
    assert status["achievement_gate"] == "ENABLED"
    assert restart_callback_state(status) == "START_RUN_PRESENT"


def test_old_bridge_status_is_explicitly_unreported():
    status = parse_status_message("bridge=1;achievement_gate=ENABLED")

    assert restart_callback_state(status) == RESTART_CALLBACK_UNREPORTED


def test_lua_bridge_probe_is_read_only_and_has_no_restart_command():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert 'restart_run_callback=" .. restart_run_callback_state()' in source
    assert 'type(G.FUNCS.start_run) == "function"' in source
    assert 'action == "RESTART_RUN"' not in source
    assert 'action == "START_RUN"' not in source
