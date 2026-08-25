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


def test_lua_bridge_restart_is_guarded_and_uses_native_setup_path():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert 'restart_run_callback=" .. restart_run_callback_state()' in source
    assert ';restart_pause_release=1' in source
    assert 'type(G.FUNCS.start_run) == "function"' in source
    assert 'action == "RESTART_RUN"' in source
    assert 'G.STATE ~= G.STATES.GAME_OVER' in source
    assert 'if G.GAME.won then' in source
    assert 'if G.GAME.seeded then' in source
    assert 'if G.GAME.challenge then' in source
    assert 'local stake = tonumber(G.GAME.stake)' in source
    assert 'G.GAME.viewed_back = nil' in source
    assert 'G.run_setup_seed = false' in source
    assert 'G.forced_stake = stake' in source
    assert 'G.FUNCS and G.FUNCS.start_setup_run' in source
    assert 'G.SETTINGS.paused = false' in source
    assert source.count('G.forced_stake = nil') >= 1
    assert 'action == "START_RUN"' not in source
