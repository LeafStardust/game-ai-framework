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
            "function love.update(dt)\n  return dt\nend\n",
        )
        archive.writestr("game.lua", "GAME_AI_TEST = true\n")
    original = prefix + payload.getvalue()
    path.write_bytes(original)
    return original, prefix


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


def test_bridge_round_trip_uses_local_file_protocol(tmp_path):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=1.0,
        poll_interval=0.001,
    )
    captured = {}

    def responder():
        deadline = time.monotonic() + 0.5
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
                bridge.response_path.write_text(
                    f"{command_id}\tOK\taccepted\n",
                    encoding="utf-8",
                )
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    bridge.play((0, 2, 4))
    thread.join(timeout=1.0)

    assert captured["action"] == "PLAY"
    assert captured["payload"] == "0,2,4"


def test_bridge_surfaces_lua_side_rejection(tmp_path):
    bridge = FirstPartyBalatroBridge(
        tmp_path,
        timeout=1.0,
        poll_interval=0.001,
    )

    def responder():
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                text = bridge.command_path.read_text(encoding="utf-8")
                command_id = text.split("\t", 1)[0]
                bridge.command_path.unlink()
                bridge.response_path.write_text(
                    f"{command_id}\tERROR\tBalatro rejected selection\n",
                    encoding="utf-8",
                )
                return
            time.sleep(0.001)

    thread = threading.Thread(target=responder)
    thread.start()
    with pytest.raises(InjectedBridgeError, match="rejected selection"):
        bridge.discard((1,))
    thread.join(timeout=1.0)


def test_fused_game_patcher_preserves_prefix_and_creates_exact_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, prefix = _write_fused_game(executable)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_text("GAME_AI_BRIDGE_TEST = true\n", encoding="utf-8")
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

    with zipfile.ZipFile(executable, "r") as archive:
        assert archive.read("game.lua") == b"GAME_AI_TEST = true\n"
        assert HOOK_BEGIN.encode("utf-8") in archive.read("main.lua")
        assert archive.read(BRIDGE_ARCHIVE_NAME) == (
            b"GAME_AI_BRIDGE_TEST = true\n"
        )


def test_fused_game_patcher_is_idempotent_and_keeps_original_backup(tmp_path):
    executable = tmp_path / "Balatro.exe"
    original, _ = _write_fused_game(executable)
    bridge_source = tmp_path / "bridge.lua"
    bridge_source.write_text("VERSION = 1\n", encoding="utf-8")
    runtime_dir = tmp_path / "runtime"

    patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=runtime_dir,
    )
    backup = backup_path(executable)
    first_backup = backup.read_bytes()

    bridge_source.write_text("VERSION = 2\n", encoding="utf-8")
    report = patch_fused_game(
        executable,
        bridge_source=bridge_source,
        runtime_dir=runtime_dir,
    )

    assert report.already_patched
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
    bridge_source.write_text("BRIDGE = true\n", encoding="utf-8")

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
    bridge_source.write_text("BRIDGE = true\n", encoding="utf-8")

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
