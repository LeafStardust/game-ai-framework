import base64
import json
from types import SimpleNamespace

import pytest

from games.mahjong_soul.live.external.capture import CaptureWriter, MahjongSoulCapture
from games.mahjong_soul.live.external.liqi import decode_envelope


def blob(number, value):
    assert len(value) < 128
    return bytes([number * 8 + 2, len(value)]) + value


def test_action_notification():
    action = b"\x08\x07" + blob(2, b"ActionDiscardTile") + blob(3, b"opaque")
    frame = b"\x01" + blob(1, b".lq.ActionPrototype") + blob(2, action)
    result = decode_envelope(frame)
    assert result["action"] == "ActionDiscardTile"
    assert result["step"] == 7
    assert base64.b64decode(result["payload_base64"]) == action


def test_response_without_method():
    result = decode_envelope(b"\x03\x34\x12" + blob(2, b"abc"))
    assert result["request_id"] == 0x1234
    assert result["method"] == ""


@pytest.mark.parametrize("frame", [b"", b"\x02", b"\x01\x0a\x05a", b"\x01\x00", b"\x01\x0a\x80"])
def test_malformed_frame(frame):
    with pytest.raises(ValueError):
        decode_envelope(frame)


def test_capture_preserves_bad_frames_and_appends(tmp_path):
    path = tmp_path / "capture.jsonl"
    writer = CaptureWriter(path)
    for content in [b"bad", b"\x03\x01\x00"]:
        writer.record(connection="a", host="example", content=content,
                      from_client=False, timestamp=1.5)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2
    assert base64.b64decode(rows[0]["raw_base64"]) == b"bad"
    assert "decode_error" in rows[0]
    assert rows[1]["liqi"]["kind"] == "response"


def test_addon_filters_hosts_and_does_not_mutate(monkeypatch, tmp_path):
    import sys

    path = tmp_path / "capture.jsonl"
    options = SimpleNamespace(mahjong_capture_hosts="mahjongsoul.com",
                              mahjong_capture_output=str(path))
    monkeypatch.setitem(sys.modules, "mitmproxy", SimpleNamespace(ctx=SimpleNamespace(options=options)))
    message = SimpleNamespace(content=b"\x03\x01\x00", from_client=False,
                              timestamp=1.0, is_text=False)
    flow = SimpleNamespace(id="one", request=SimpleNamespace(host="evilmahjongsoul.com"),
                           websocket=SimpleNamespace(messages=[message]))
    addon = MahjongSoulCapture()
    addon.websocket_message(flow)
    assert not path.exists()
    flow.request.host = "game.mahjongsoul.com"
    addon.websocket_message(flow)
    assert path.exists()
    assert message.content == b"\x03\x01\x00"
