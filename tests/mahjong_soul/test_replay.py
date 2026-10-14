import base64
import json
import sys

import pytest

from games.mahjong_soul.live.runtime.replay import main
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper


def test_replay_keeps_source_and_refuses_existing_output(tmp_path, monkeypatch):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema().document))
    source, output = tmp_path / "raw.jsonl", tmp_path / "decoded.jsonl"
    frame = wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"0m")))
    original = json.dumps({"connection": "one", "host": "example", "direction": "server",
                           "timestamp": 1, "raw_base64": base64.b64encode(frame).decode()}) + "\n"
    source.write_text(original)
    monkeypatch.setattr(sys, "argv", ["replay", str(source), "--schema", str(schema_path),
                                      "--output", str(output), "--seat", "0"])
    main()
    assert json.loads(output.read_text())["state"]["hand"] == ["0m"]
    assert source.read_text() == original
    with pytest.raises(SystemExit):
        main()


def test_replay_preserves_connection_close(tmp_path, monkeypatch):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema().document))
    source, output = tmp_path / "raw.jsonl", tmp_path / "decoded.jsonl"
    frame = wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"0m")))
    rows = [{"connection": "one", "host": "example", "direction": "server",
             "timestamp": 1, "raw_base64": base64.b64encode(frame).decode()},
            {"event": "connection_closed", "connection": "one", "timestamp": 2}]
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    monkeypatch.setattr(sys, "argv", ["replay", str(source), "--schema", str(schema_path),
                                      "--output", str(output), "--seat", "0"])
    main()
    decoded = [json.loads(line) for line in output.read_text().splitlines()]
    assert decoded[-1]["event"] == "connection_closed"
    assert decoded[-1]["timestamp"] == 2
    assert decoded[-1]["state"]["status"] == "incomplete"
    assert decoded[-1]["state"]["operations"] is None


@pytest.mark.parametrize("row", [[], {"connection": "game", "event": "unknown"},
                                 {"connection": "game", "direction": "sideways"}])
def test_replay_rejects_invalid_capture_metadata(tmp_path, monkeypatch, row):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema().document))
    source = tmp_path / "raw.jsonl"
    source.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(sys, "argv", ["replay", str(source), "--schema", str(schema_path),
                                      "--output", str(tmp_path / "decoded.jsonl")])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_replay_preserves_text_frame_diagnostic(tmp_path, monkeypatch):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema().document))
    source, output = tmp_path / "raw.jsonl", tmp_path / "decoded.jsonl"
    # Even protobuf-shaped bytes must stay a text-frame diagnostic.
    frame = wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))
    source.write_text(json.dumps({"connection": "game", "host": "example",
                                 "direction": "server", "timestamp": 1, "is_text": True,
                                 "raw_base64": base64.b64encode(frame).decode()}) + "\n")
    monkeypatch.setattr(sys, "argv", ["replay", str(source), "--schema", str(schema_path),
                                      "--output", str(output), "--seat", "0"])
    main()
    result = json.loads(output.read_text())
    assert result["is_text"] is True
    assert result["decode_error"] == "Text WebSocket message"
    assert result["state"]["hand"] == []
