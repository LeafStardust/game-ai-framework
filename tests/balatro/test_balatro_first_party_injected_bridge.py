import io
import threading
import time
import zipfile

import pytest

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    encode_command,
    parse_response,
    parse_status_message,
)
from games.balatro.live.injected.install import (
    BRIDGE_ARCHIVE_NAME,
    HOOK_BEGIN,
    BalatroFusedPatchError,
    asset_dir,
    backup_path,
    patch_fused_game,
    restore_fused_game,
)


def _write_fused_game(path):
    prefix = b"MZ" + b"\x00" * 510
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "main.lua",
            b"function love.update(dt)\n  return dt\nend\n",
        )
        archive.writestr("game.lua", b"GAME_AI_TEST = true\n")
    original = prefix + payload.getvalue()
    path.write_bytes(original)
    return original, prefix


def _write_bridge_response(bridge, text):
    temporary = bridge.response_path.with_name(
        bridge.response_path.name + ".tmp"
    )
    temporary.write_bytes(text.encode("utf-8"))
    temporary.replace(bridge.response_path)


def test_command_protocol_uses_zero_based_hand_indices():
    command = encode_command("abc123", "play", (0, 2, 4))
    assert command == "abc123\tPLAY\t0,2,4\n"


def test_response_protocol_preserves_bridge_error():
    command_id, status, message = parse_response(
        "abc123\tERROR\tplay_button not found\n"
    )
    assert command_id == "abc123"
    assert status == "ERROR"
    assert message == "play_button not found"


def test_status_protocol_parses_bridge_and_achievement_gate():
    status = parse_status_message("bridge=1;achievement_gate=ENABLED")
    assert status == {
        "bridge": "1",
        "achievement_gate": "ENABLED",
    }


def test_bridge_round_trip_uses_local_file_protocol(tmp_path):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=5.0,
        poll_interval=0.001,
    )
    captured = {}
    responder_ready = threading.Event()

    def responder():
        responder_ready.set()
        deadline = time.monotonic() + bridge.timeout + 1.0
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                text = bridge.command_path.read_text(encoding="utf-8")
                command_id, action, payload = text.rstrip("\n").split("\t", 2)
                captured.update(
                    command_id=command_id,
                    action=action,
                    payload=payload,
                )
                bridge.command_path.unlink()
                _write_bridge_response(
                    bridge,
                    f"{command_id}\tOK\taccepted\n",
                )
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    assert responder_ready.wait(timeout=1.0)
    bridge.play((0, 2, 4))
    thread.join(timeout=bridge.timeout + 1.0)

    assert not thread.is_alive()
    assert captured["action"] == "PLAY"
    assert captured["payload"] == "0,2,4"


def test_bridge_status_round_trip_is_non_gameplay_command(tmp_path):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=5.0,
        poll_interval=0.001,
    )
    captured = {}
    responder_ready = threading.Event()

    def responder():
        responder_ready.set()
        # Match the other synthetic bridge round-trip tests: under the complete
        # Balatro suite the responder thread can be scheduler-delayed even though
        # the file protocol itself is correct. Keep the peer alive beyond the
        # client's timeout so a busy runner does not turn this into a false bridge
        # failure.
        deadline = time.monotonic() + bridge.timeout + 1.0
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                text = bridge.command_path.read_text(encoding="utf-8")
                command_id, action, payload = text.rstrip("\n").split("\t", 2)
                captured.update(action=action, payload=payload)
                bridge.command_path.unlink()
                _write_bridge_response(
                    bridge,
                    f"{command_id}\tOK\tbridge=1;achievement_gate=UNSET\n",
                )
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    assert responder_ready.wait(timeout=1.0)
    status = bridge.status()
    thread.join(timeout=bridge.timeout + 1.0)

    assert not thread.is_alive()
    assert captured == {"action": "STATUS", "payload": ""}
    assert status["bridge"] == "1"
    assert status["achievement_gate"] == "UNSET"


def test_bridge_surfaces_lua_side_rejection(tmp_path):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=5.0,
        poll_interval=0.001,
    )
    responder_ready = threading.Event()
    response_written = threading.Event()

    def responder():
        responder_ready.set()
        # The responder must outlive the client's timeout window; otherwise full-suite
        # scheduler contention can let the peer exit before the command is observed.
        deadline = time.monotonic() + bridge.timeout + 2.0
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                text = bridge.command_path.read_text(encoding="utf-8")
                command_id = text.split("\t", 1)[0]
                bridge.command_path.unlink()
                _write_bridge_response(
                    bridge,
                    f"{command_id}\tERROR\tBalatro rejected selection\n",
                )
                response_written.set()
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    assert responder_ready.wait(timeout=1.0)
    with pytest.raises(InjectedBridgeError) as captured:
        bridge.discard((1,))
    thread.join(timeout=bridge.timeout + 2.5)

    assert response_written.is_set(), (
        "synthetic Lua responder never wrote its rejection; this is a test-harness "
        "timing failure, not a bridge error-propagation failure"
    )
    assert not thread.is_alive()
    assert str(captured.value) == "Balatro rejected selection"


def test_fused_game_patcher_preserves_prefix_and_creates_exact_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, prefix = _write_fused_game(executable)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"GAME_AI_BRIDGE_TEST = true\n")
    runtime_dir = tmp_path / "runtime"

    report = patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=runtime_dir,
    )

    assert report.backup.read_bytes() == original
    assert executable.read_bytes().startswith(prefix)
    assert report.runtime_dir == runtime_dir
    assert not report.already_patched
    assert not report.reused_backup

    with zipfile.ZipFile(executable, "r") as archive:
        assert archive.read("game.lua") == b"GAME_AI_TEST = true\n"
        assert HOOK_BEGIN.encode("utf-8") in archive.read("main.lua")
        assert archive.read(BRIDGE_ARCHIVE_NAME) == (
            b"GAME_AI_BRIDGE_TEST = true\n"
        )


def test_fused_game_patcher_reuses_identical_interrupted_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, _ = _write_fused_game(executable)
    backup = backup_path(executable)
    backup.write_bytes(original)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"BRIDGE = true\n")

    report = patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=tmp_path / "runtime",
    )

    assert report.reused_backup
    assert backup.read_bytes() == original
    with zipfile.ZipFile(executable, "r") as archive:
        assert HOOK_BEGIN.encode("utf-8") in archive.read("main.lua")


def test_fused_game_patcher_rejects_different_existing_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    _write_fused_game(executable)
    backup_path(executable).write_bytes(b"different backup")
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"BRIDGE = true\n")

    with pytest.raises(BalatroFusedPatchError, match="differs from the current"):
        patch_fused_game(
            executable,
            bridge_source=bridge_source,
            runtime_dir=tmp_path / "runtime",
        )


def test_fused_game_patcher_is_idempotent_and_keeps_original_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, _ = _write_fused_game(executable)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"VERSION = 1\n")
    runtime_dir = tmp_path / "runtime"

    patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=runtime_dir,
    )
    backup = backup_path(executable)
    first_backup = backup.read_bytes()

    bridge_source.write_bytes(b"VERSION = 2\n")
    report = patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=runtime_dir,
    )

    assert report.already_patched
    assert not report.reused_backup
    assert first_backup == original
    assert backup.read_bytes() == original
    with zipfile.ZipFile(executable, "r") as archive:
        assert archive.read("main.lua").count(
            HOOK_BEGIN.encode("utf-8")
        ) == 1
        assert archive.read(BRIDGE_ARCHIVE_NAME) == b"VERSION = 2\n"


def test_restore_fused_game_restores_exact_original_bytes(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, _ = _write_fused_game(executable)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"BRIDGE = true\n")

    patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=tmp_path / "runtime",
    )
    restore_fused_game(executable)

    assert executable.read_bytes() == original
    assert not backup_path(executable).exists()


def test_fused_game_patcher_rejects_non_fused_executable(tmp_path):
    executable = tmp_path / "Balatro.exe"
    executable.write_bytes(b"MZ" + b"\x00" * 128)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_bytes(b"BRIDGE = true\n")

    with pytest.raises(BalatroFusedPatchError, match="fused LÖVE archive"):
        patch_fused_game(
            executable,
            bridge_source=bridge_source,
            runtime_dir=tmp_path / "runtime",
        )


def test_bridge_asset_has_no_external_mod_or_network_dependency():
    lua = (asset_dir() / "bridge.lua").read_text(encoding="utf-8")

    assert "SMODS." not in lua
    assert 'require("socket")' not in lua
    assert 'require("json")' not in lua
    assert "play_cards_from_highlighted" in lua
    assert "discard_cards_from_highlighted" in lua
    assert 'action == "STATUS"' in lua
    assert "F_NO_ACHIEVEMENTS" in lua
