from games.balatro.live.injected.install import bridge_asset_path


def test_bridge_status_identifies_hardened_command_pump():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert (
        'return "bridge=2;bridge_revision=5;blind_skip=1;hand_reorder=1;'
        'achievement_gate="' in source
    )
    assert 'command_pump=LOVE_RUN_PRE_UPDATE' in source


def test_bridge_polls_before_balatro_update_and_from_outer_frame_loop():
    source = bridge_asset_path().read_text(encoding="utf-8")

    update_wrapper = source.index("love.update = function(dt)")
    update_poll = source.index("safe_poll_bridge()", update_wrapper)
    original_update = source.index("original_love_update(dt)", update_wrapper)
    assert update_poll < original_update

    assert "local original_love_run = love.run" in source
    assert 'if type(original_love_run) == "function" then' in source
    assert "local frame = original_love_run(...)" in source
    assert 'if type(frame) ~= "function" then' in source
    assert "safe_poll_bridge()\n        return frame(...)" in source


def test_redundant_pump_remains_single_consumer():
    source = bridge_asset_path().read_text(encoding="utf-8")

    # read_command removes the slot before dispatch. A second pump in the same
    # frame therefore cannot observe and execute the same command twice.
    read_start = source.index("local function read_command()")
    read_end = source.index("local function parse_indices", read_start)
    read_source = source[read_start:read_end]
    assert "os.remove(command_path)" in read_source
