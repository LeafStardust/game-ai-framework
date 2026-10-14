import base64
import json

from games.mahjong_soul.live.runtime.reader import GameReader
from games.mahjong_soul.live.runtime.monitor import CaptureTail, render
from games.mahjong_soul.live.runtime.state import GameState
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper


def record(frame, connection="game", client=False):
    return {"connection": connection, "raw_base64": base64.b64encode(frame).decode(),
            "direction": "client" if client else "server"}


def test_reader_keeps_game_when_lobby_decoder_fails():
    reader = GameReader(schema(), seat=0)
    frame = wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))
    reader.consume(record(frame))
    failure = reader.consume(record(wrapper(1, ".lq.UnknownLobby", b""), connection="lobby"))
    assert "schema_warning" in failure["liqi"]
    summary = reader.snapshot()
    assert summary["state"]["status"] == "tracking"
    assert summary["state"]["hand"] == ["1m"]
    assert summary["schema_warnings"][0]["method"] == ".lq.UnknownLobby"
    reader.close_connection("game")
    assert reader.snapshot()["state"]["hand"] == ["1m"]


def test_unreadable_game_event_invalidates_current_game():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    reader.consume(record(wrapper(1, ".lq.ActionUnknown", b"")))
    assert reader.snapshot()["state"]["status"] == "incomplete"


def test_game_end_notification_clears_operations():
    document = schema().document
    document["nested"]["lq"]["nested"]["NotifyGameEndResult"] = {"fields": {}}
    from games.mahjong_soul.live.external.schema import LiqiSchema
    reader = GameReader(LiqiSchema(document), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    reader.consume(record(wrapper(1, ".lq.NotifyGameEndResult", b"")))
    assert reader.snapshot()["state"]["status"] == "match_ended"
    assert reader.snapshot()["state"]["operations"] is None


def test_tail_waits_for_complete_line_and_handles_truncation(tmp_path):
    path = tmp_path / "capture.jsonl"
    tail = CaptureTail(path)
    row = record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m"))))
    encoded = json.dumps(row).encode()
    path.write_bytes(encoded[:10])
    assert tail.read() == []
    with path.open("ab") as stream:
        stream.write(encoded[10:] + b"\n")
    assert tail.read() == [row]
    assert tail.read() == []
    path.write_bytes(b"not-json\n")
    assert tail.read() == []
    assert tail.reset is True
    assert tail.bad_rows == 1


def test_monitor_render_uses_three_seats_and_retains_diagnostics():
    reader = GameReader(schema(), seat=0)
    payload = blob(4, b"0m") + blob(6, b"\xb8\x91\x02" * 3)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", payload))))
    reader.consume(record(wrapper(1, ".lq.UnknownLobby", b""), connection="lobby"))
    display = render(reader.snapshot())
    assert "Players: 3" in display
    assert "Seat 2:" in display and "Seat 3:" not in display
    assert "Hand: 0m" in display
    assert ".lq.UnknownLobby" in display


def event(name, data, step):
    return {"name": name, "data": data, "step": step}


def test_called_discard_marked_without_losing_river_history():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": ["3m", "4m", "9p"]}, 0))
    state.apply(event("ActionDiscardTile", {"seat": 3, "tile": "2m"}, 1))
    state.apply(event("ActionChiPengGang", {"seat": 0, "type": 0,
                      "tiles": ["2m", "3m", "4m"], "froms": [3, 0, 0]}, 2))
    assert state.discards[3] == [{"tile": "2m", "riichi": False, "tsumogiri": False, "called": True}]
    assert state.hand == ["9p"]
    assert state.status == "tracking"


def test_exhaustive_draw_bool_gameend_and_score_vectors():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"scores": [25000] * 4, "tiles": ["1m"]}, 0))
    state.apply(event("ActionNoTile", {"gameend": False,
                      "scores": [{"old_scores": [25000] * 4, "delta_scores": [1500, -1500, -1500, 1500]}]}, 1))
    assert state.scores == [26500, 23500, 23500, 26500]
    assert state.status == "round_ended"


def test_multiple_draw_settlements_are_flagged_instead_of_guessed():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"scores": [25000] * 4, "tiles": ["1m"]}, 0))
    state.apply(event("ActionNoTile", {"gameend": True, "scores": [{}, {}]}, 1))
    assert state.status == "incomplete"
    assert state.scores == [25000] * 4


def test_riichi_declaration_acceptance_and_drawn_tile():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"scores": [35000] * 3, "tiles": ["1m"]}, 0))
    state.apply(event("ActionDealTile", {"seat": 0, "tile": "0p", "zhenting": False}, 1))
    assert state.drawn_tile == "0p"
    state.apply(event("ActionDiscardTile", {"seat": 0, "tile": "1m", "is_liqi": True}, 2))
    assert state.drawn_tile is None and state.riichi[0] == "declared"
    state.apply(event("ActionDealTile", {"seat": 1, "tile": "", "liqi": {"seat": 0, "score": 34000, "liqibang": 1}}, 3))
    assert state.riichi[0] == "accepted"
    assert state.scores == [34000, 35000, 35000]
    assert state.round["liqibang"] == 1


def test_exhaustive_draw_without_deltas_keeps_scores():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"scores": [25000] * 4, "tiles": ["1m"]}, 0))
    state.apply(event("ActionNoTile", {"gameend": False, "scores": [{"old_scores": [25000] * 4}]}, 1))
    assert state.scores == [25000] * 4
    assert state.status == "round_ended"


def test_visible_tiles_do_not_double_count_called_river_tile():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": ["3m", "4m", "0p"], "doras": ["9s"]}, 0))
    state.apply(event("ActionDiscardTile", {"seat": 3, "tile": "2m"}, 1))
    state.apply(event("ActionChiPengGang", {"seat": 0, "type": 0,
                      "tiles": ["2m", "3m", "4m"], "froms": [3, 0, 0]}, 2))
    counts, complete = state.visible_tiles()
    assert counts == {"2m": 1, "3m": 1, "4m": 1, "5p": 1, "9s": 1}
    assert complete is True


def test_snapshot_unknown_called_flags_mark_visibility_incomplete():
    from tests.mahjong_soul.test_kan_restore import snapshot
    state = GameState(0)
    state.restore(snapshot())
    assert state.snapshot()["visibility_complete"] is False
    assert state.snapshot()["visible_tile_counts"]["5s"] == 3


def test_opponent_concealed_kan_does_not_invent_four_red_fives():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": ["1m"]}, 0))
    state.apply(event("ActionAnGangAddGang", {"seat": 1, "type": 3, "tiles": "0p"}, 1))
    assert state.melds[1][0]["tiles"] == ["5p"] * 4
    assert state.melds[1][0]["red_fives_known"] is False
    assert state.visible_tiles()[0]["5p"] == 4


def test_reader_flags_impossible_visible_tiles():
    reader = GameReader(schema(), seat=0)
    payload = blob(4, b"1m") * 5
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", payload))))
    state = reader.snapshot()["state"]
    assert state["status"] == "incomplete"
    assert "Visible tile count exceeds four copies" in state["issues"]
    assert state["visibility_complete"] is False


def test_reader_flags_invalid_tile_strings():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"0z")))))
    assert "Visible state contains an invalid tile" in reader.snapshot()["state"]["issues"]


def test_old_connection_traffic_cannot_replace_new_active_game():
    document = schema().document
    document["nested"]["lq"]["nested"]["NotifyGameEndResult"] = {"fields": {}}
    from games.mahjong_soul.live.external.schema import LiqiSchema
    reader = GameReader(LiqiSchema(document), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m"))), connection="old"))
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"2p"))), connection="new"))
    reader.consume(record(wrapper(2, ".lq.FastTest.syncGame", b""), connection="old", client=True))
    reader.consume(record(wrapper(1, ".lq.NotifyGameEndResult", b""), connection="old"))
    assert reader.snapshot()["game_connection"] == "new"
    assert reader.snapshot()["state"]["hand"] == ["2p"]
    assert reader.snapshot()["state"]["status"] == "tracking"


def test_connection_close_clears_operations_and_keeps_last_hand():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    result = reader.consume({"event": "connection_closed", "connection": "game"})
    assert result["state"]["status"] == "incomplete"
    assert reader.snapshot()["connection_open"] is False
    assert reader.snapshot()["state"]["hand"] == ["1m"]
    assert reader.snapshot()["state"]["operations"] is None
    assert reader.snapshot()["closed_connections"] == 1


def test_tail_accepts_connection_control_rows(tmp_path):
    path = tmp_path / "capture.jsonl"
    row = {"event": "connection_closed", "connection": "game"}
    path.write_text(json.dumps(row) + "\n")
    assert CaptureTail(path).read() == [row]


def test_unknown_lobby_rpc_response_keeps_method_correlation():
    reader = GameReader(schema(), seat=0)
    request = wrapper(2, ".lq.Lobby.newLobbyMethod", b"", request_id=17)
    response = wrapper(3, "", b"", request_id=17)
    reader.consume(record(request, connection="lobby", client=True))
    result = reader.consume(record(response, connection="lobby"))
    assert result["liqi"]["method"] == ".lq.Lobby.newLobbyMethod"
    assert "schema_warning" in result["liqi"]
    assert reader.snapshot()["decode_errors"] == []
    assert len(reader.snapshot()["schema_warnings"]) == 2


def test_unknown_game_rpc_is_not_downgraded_to_lobby_warning():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    result = reader.consume(record(wrapper(2, ".lq.FastTest.newGameMethod", b""), client=True))
    assert "decode_error" in result
    assert reader.snapshot()["state"]["status"] == "incomplete"


def test_authentication_resets_old_board_on_reused_connection():
    reader = GameReader(schema())
    reader.consume(record(wrapper(2, ".lq.FastTest.authGame", b"\x08\x2a", request_id=1), client=True))
    reader.consume(record(wrapper(3, "", blob(3, b"\x2a\x00\x00\x00"), request_id=1)))
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    reader.consume(record(wrapper(2, ".lq.FastTest.authGame", b"\x08\x2a", request_id=2), client=True))
    reader.consume(record(wrapper(3, "", blob(3, b"\x00\x2a\x00"), request_id=2)))
    state = reader.snapshot()["state"]
    assert state["seat"] == 1 and state["player_count"] == 3
    assert state["hand"] == [] and state["scores"] == []
    assert state["status"] == "waiting_for_round"
    assert reader.snapshot()["last_event"] is None
