import json
import struct
import zlib
import pytest
from games.mahjong_soul.live.runtime.calibration import EvidenceRecorder, context
from games.mahjong_soul.live.runtime.windows_recording import png_from_bgra


def report(step=4):
    return {"state_ready": True, "connection_open": True, "game_connection": "game",
            "game_generation": 2, "state": {"step": step, "seat": 1, "round": {"ju": 0},
            "hand": ["1m"], "operations": {"seat": 1, "operation_list": [{"type": 1}]}},
            "last_event": {"name": "ActionDealTile"}, "authentication_secret": "never save"}


def rows(path):
    return [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]


def test_frame_dedup_click_context_and_conservative_confirmation(tmp_path):
    path = tmp_path / "record"; r = EvidenceRecorder(path)
    geometry = {"width": 100, "height": 100, "left": 30, "top": 40}
    r.frame(report(), geometry, b"image", 1)
    r.frame(report(), geometry, b"image", 1.1)
    r.click(report(), geometry, 50, 60, 1.2)
    r.action(report(5), "game", {"source": "live", "name": "ActionDiscardTile", "step": 5,
                               "data": {"seat": 1, "tile": "1m", "secret": "never save"}}, 1.4)
    r.close(); data = rows(path)
    assert [x["kind"] for x in data] == ["frame", "click", "action"]
    assert data[1]["preceding_image"] == "frame-000001.png"
    assert data[2]["candidate_click_ids"] == [data[1]["id"]]
    assert data[2]["needs_review"] is True
    assert "secret" not in (path / "events.jsonl").read_text()


@pytest.mark.parametrize("change", ["connection", "generation", "step", "timeout", "opponent"])
def test_unrelated_actions_do_not_confirm_clicks(tmp_path, change):
    r = EvidenceRecorder(tmp_path / "record")
    g = {"width": 100, "height": 100}
    r.click(report(), g, 1, 1, 1)
    s = report(5); connection = "game"; now = 2; seat = 1; step = 5
    if change == "connection": connection = "other"
    if change == "generation": s["game_generation"] = 3
    if change == "step": step = 6
    if change == "timeout": now = 10
    if change == "opponent": seat = 2
    r.action(s, connection, {"source": "live", "name": "ActionDiscardTile", "step": step,
                           "data": {"seat": seat, "tile": "1m"}}, now)
    r.close()
    assert all(not row.get("candidate_click_ids") for row in rows(tmp_path / "record"))


def test_old_or_moved_frame_is_not_presented_as_preclick_evidence(tmp_path):
    r = EvidenceRecorder(tmp_path / "record"); g = {"width": 100, "height": 100, "left": 0}
    r.frame(report(), g, b"image", 1)
    r.click(report(), g, 1, 1, 2)
    r.click(report(), {**g, "left": 10}, 1, 1, 1.2)
    r.close()
    assert all(x["preceding_image"] is None for x in rows(tmp_path / "record") if x["kind"] == "click")


def test_disk_limit_stops_before_writing_image(tmp_path):
    path = tmp_path / "record"; r = EvidenceRecorder(path, max_bytes=2)
    with pytest.raises(RuntimeError, match="limit"):
        r.frame(report(), {"width": 100, "height": 100}, b"too big", 1)
    r.close(); assert not list(path.glob("*.png"))


def test_png_preserves_rgb_channel_order():
    png = png_from_bgra(bytes([1, 2, 3, 255]), 1, 1)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8; compressed = b""
    while offset < len(png):
        size = struct.unpack(">I", png[offset:offset+4])[0]
        if png[offset+4:offset+8] == b"IDAT": compressed += png[offset+8:offset+8+size]
        offset += size+12
    assert zlib.decompress(compressed) == bytes([0, 3, 2, 1])
