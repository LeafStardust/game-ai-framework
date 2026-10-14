from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from games.mahjong_soul.live.runtime.reader import GameReader
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper
from tests.mahjong_soul.test_reader_monitor import record


def test_no_game_has_no_board_and_is_not_ready():
    result = observation_from_snapshot(GameReader(schema()).snapshot())
    assert result["version"] == 1
    assert result["board"] is None and not result["ready"]
    assert result["status"] == "waiting_for_game"


def test_observation_preserves_seats_unknowns_operations_and_isolation():
    reader = GameReader(schema(), seat=2)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"0p")))))
    state = reader.connections["game"][1]
    state.operations = {"seat": 2, "operation_list": [{"type": 999, "combination": ["0p|5p"]}], "time_fixed": 7}
    report = reader.snapshot()
    result = observation_from_snapshot(report)
    assert result["ready"]
    board = result["board"]
    assert board["self_seat"] == 2
    assert [p["is_self"] for p in board["players"]] == [False, False, True, False]
    assert board["players"][0]["score"] is None
    assert board["self"]["hand"] == ["0p"]
    assert board["visible_tile_counts"] == {"5p": 1}
    assert board["available_operations"] == state.operations
    assert all("hand" not in player for player in board["players"])
    board["self"]["hand"].clear()
    board["available_operations"]["operation_list"].clear()
    assert report["state"]["hand"] == ["0p"]
    assert reader.snapshot()["state"]["operations"]["operation_list"]


def test_three_player_observation_and_disconnected_board():
    reader = GameReader(schema(), seat=0)
    reader.consume(record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m")))))
    reader.connections["game"][1].__init__(0, 3)
    reader.close_connection("game")
    result = observation_from_snapshot(reader.snapshot())
    assert len(result["board"]["players"]) == 3
    assert not result["ready"]
    assert not result["source"]["connection_open"]
    assert result["board"]["available_operations"] is None
    assert result["issues"]
