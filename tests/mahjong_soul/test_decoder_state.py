import base64
import json

import pytest

from games.mahjong_soul.live.external.capture import CaptureWriter
from games.mahjong_soul.live.external.decoder import LiqiDecoder, action_bytes
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.state import GameState


def varint(value):
    output = bytearray()
    while value > 127:
        output.append((value & 127) | 128)
        value >>= 7
    output.append(value)
    return bytes(output)


def blob(number, value):
    return varint(number * 8 + 2) + varint(len(value)) + value


def schema():
    def message(**specs):
        return {"fields": {name: {"id": number, "type": kind, **({"rule": "repeated"} if repeated else {})}
                           for name, (number, kind, repeated) in specs.items()}}
    return LiqiSchema({"nested": {"lq": {"nested": {
        "ActionPrototype": message(step=(1, "uint32", False), name=(2, "string", False), data=(3, "bytes", False)),
        "ActionNewRound": message(ju=(2, "uint32", False), tiles=(4, "string", True), scores=(6, "int32", True)),
        "ActionDealTile": message(seat=(1, "uint32", False), tile=(2, "string", False)),
        "ActionDiscardTile": message(seat=(1, "uint32", False), tile=(2, "string", False), moqie=(5, "bool", False)),
        "ReqAuthGame": message(account_id=(1, "uint32", False)),
        "ResAuthGame": message(seat_list=(3, "uint32", True)),
        "GameRestore": message(actions=(2, "ActionPrototype", True)),
        "ResSync": message(game_restore=(1, "GameRestore", False)),
        "Empty": message(),
        "FastTest": {"methods": {
            "authGame": {"requestType": "ReqAuthGame", "responseType": "ResAuthGame"},
            "syncGame": {"requestType": "Empty", "responseType": "ResSync"}}},
    }}}})


def wrapper(kind, method, payload, request_id=1):
    header = bytes([kind]) + (request_id.to_bytes(2, "little") if kind != 1 else b"")
    return header + blob(1, method.encode()) + blob(2, payload)


def action(name, payload, step=0, encoded=True):
    data = action_bytes(payload) if encoded else payload
    return b"\x08" + varint(step) + blob(2, name.encode()) + blob(3, data)


def test_packed_signed_numbers_defaults_and_unknown_fields():
    decoded = schema().decode("lq.ActionNewRound", blob(6, varint(25000) + varint((1 << 64) - 1000)) + b"\xa0\x01\x07")
    assert decoded == {"ju": 0, "tiles": [], "scores": [25000, -1000]}


def test_live_xor_and_restore_plain_paths():
    decoder = LiqiDecoder(schema())
    payload = blob(2, b"5m")
    live = decoder.decode(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", payload, 2)), False)
    assert live["events"][0]["data"] == {"seat": 0, "tile": "5m", "moqie": False}
    decoder.decode(wrapper(2, ".lq.FastTest.syncGame", b""), True)
    restore = blob(1, blob(2, action("ActionDiscardTile", payload, 2, encoded=False)))
    response = decoder.decode(wrapper(3, "", restore), False)
    assert response["events"][0]["source"] == "restore"
    assert response["events"][0]["data"]["tile"] == "5m"


def test_response_correlation_is_connection_and_direction_scoped():
    first, second = LiqiDecoder(schema()), LiqiDecoder(schema())
    first.decode(wrapper(2, ".lq.FastTest.authGame", b"\x08\x2a"), True)
    response = wrapper(3, "", blob(3, b"\x00\x2a\x00\x00"))
    with pytest.raises(ValueError, match="Unmatched"):
        second.decode(response, False)
    with pytest.raises(ValueError, match="Unmatched"):
        first.decode(response, True)
    assert first.decode(response, False)["own_seat"] == 1


def test_capture_updates_hand_and_auto_seat(tmp_path):
    writer = CaptureWriter(tmp_path / "capture.jsonl", schema())
    def record(content, client=False):
        return writer.record(connection="game", host="game.mahjongsoul.com", content=content,
                             from_client=client, timestamp=1)
    record(wrapper(2, ".lq.FastTest.authGame", b"\x08\x2a"), True)
    record(wrapper(3, "", blob(3, b"\x00\x2a\x00\x00")))
    record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"5m"))))
    draw = b"\x08\x01" + blob(2, b"0m")
    record(wrapper(1, ".lq.ActionPrototype", action("ActionDealTile", draw, 1)))
    discard = b"\x08\x01" + blob(2, b"5m")
    row = record(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", discard, 2)))
    assert row["state"]["seat"] == 1
    assert row["state"]["hand"] == ["0m"]
    assert row["state"]["status"] == "tracking"
    assert len([json.loads(line) for line in writer.path.read_text().splitlines()]) == 5
    writer.close_connection("game")
    assert not writer.connections


def test_hidden_draw_gaps_duplicates_and_round_reset():
    state = GameState(0)
    def event(name, data, step):
        return {"name": name, "data": data, "step": step}
    state.apply(event("ActionNewRound", {"tiles": ["1m"], "ju": 0}, 0))
    state.apply(event("ActionDealTile", {"seat": 1, "tile": ""}, 1))
    assert state.hand == ["1m"]
    state.apply(event("ActionDiscardTile", {"seat": 1, "tile": "9s"}, 3))
    assert state.status == "incomplete"
    state.apply(event("ActionDiscardTile", {"seat": 1, "tile": "9s"}, 3))
    assert len(state.discards[1]) == 1
    state.apply(event("ActionNewRound", {"tiles": ["2p"], "ju": 1}, 0))
    assert state.status == "tracking"
    assert not state.issues


def test_meld_removes_only_own_tiles_and_unknown_action_invalidates():
    state = GameState(0)
    state.apply({"name": "ActionNewRound", "step": 0, "data": {"tiles": ["3m", "4m", "9p"]}})
    state.apply({"name": "ActionChiPengGang", "step": 1,
                 "data": {"seat": 0, "tiles": ["2m", "3m", "4m"], "froms": [3, 0, 0]}})
    assert state.hand == ["9p"]
    state.apply({"name": "ActionUnknown", "step": 2, "data": {}})
    assert state.status == "incomplete"


def test_schema_rejects_wrong_wire_and_truncated_packed():
    with pytest.raises(ValueError, match="wire"):
        schema().decode("lq.ActionDealTile", b"\x10\x01")
    with pytest.raises(ValueError, match="Truncated"):
        schema().decode("lq.ActionNewRound", blob(6, b"\x80"))
