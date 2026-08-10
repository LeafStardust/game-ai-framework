import json

from games.balatro.live import (
    FileBalatroBridge,
    LiveBalatroCommand,
)


def test_file_bridge_reads_live_snapshot(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "sequence": 7,
                "phase": "3",
                "state_complete": True,
                "payload": {
                    "money": 12,
                    "ante": 2,
                },
            }
        ),
        encoding="utf-8",
    )

    bridge = FileBalatroBridge(tmp_path)
    snapshot = bridge.observe()

    assert snapshot.sequence == 7
    assert snapshot.phase == "3"
    assert snapshot.state_complete
    assert snapshot.payload["money"] == 12
    assert snapshot.payload["ante"] == 2


def test_file_bridge_reports_connection_from_state_file(tmp_path):
    bridge = FileBalatroBridge(tmp_path)

    assert not bridge.is_connected()

    (tmp_path / "state.json").write_text("{}", encoding="utf-8")

    assert bridge.is_connected()


def test_file_bridge_writes_command_atomically(tmp_path):
    bridge = FileBalatroBridge(tmp_path)
    bridge.send(
        LiveBalatroCommand(
            sequence=4,
            action="PLAY_CARDS",
            payload={"cards": ["card-1"]},
        )
    )

    command = json.loads(
        (tmp_path / "command.json").read_text(encoding="utf-8")
    )

    assert command == {
        "sequence": 4,
        "action": "PLAY_CARDS",
        "payload": {"cards": ["card-1"]},
    }
    assert not (tmp_path / "command.tmp").exists()
