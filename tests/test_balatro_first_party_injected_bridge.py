import threading
import time

import pytest

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    encode_command,
    parse_response,
)
from games.balatro.live.injected.install import (
    ASSET_NAMES,
    asset_dir,
    install_bridge_assets,
)


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


def test_bridge_assets_are_first_party_and_do_not_require_balatrobot(tmp_path):
    destination = install_bridge_assets(tmp_path / "mod")

    assert {path.name for path in destination.iterdir()} == set(ASSET_NAMES)
    lua = (destination / "bridge.lua").read_text(encoding="utf-8")
    lovely = (destination / "lovely.toml").read_text(encoding="utf-8")

    assert "SMODS." not in lua
    assert 'require("socket")' not in lua
    assert 'require("json")' not in lua
    assert "play_cards_from_highlighted" in lua
    assert "discard_cards_from_highlighted" in lua
    assert 'target = "main.lua"' in lovely
    assert asset_dir().is_dir()
