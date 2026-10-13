import pytest

from games.mahjong_soul.live.external.capture import CaptureWriter
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.state import GameState
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper


def event(name, data, step):
    return {"name": name, "data": data, "step": step}


def test_concealed_kan_keeps_red_five_and_duplicate_is_ignored():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": ["0m", "5m", "5m", "5m", "2p"]}, 0))
    kan = event("ActionAnGangAddGang", {"seat": 0, "type": 3, "tiles": "5m"}, 1)
    state.apply(kan)
    state.apply(kan)
    assert state.hand == ["2p"]
    assert state.melds[0][0]["tiles"] == ["0m", "5m", "5m", "5m"]
    assert len(state.melds[0]) == 1
    assert state.status == "tracking"


def test_added_kan_upgrades_pon_and_removes_single_red_tile():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": ["5m", "5m", "0m", "2p"]}, 0))
    state.apply(event("ActionChiPengGang", {"seat": 0, "type": 1,
                      "tiles": ["5m", "5m", "5m"], "froms": [1, 0, 0]}, 1))
    state.apply(event("ActionAnGangAddGang", {"seat": 0, "type": 2, "tiles": "5m"}, 2))
    assert state.hand == ["2p"]
    assert len(state.melds[0]) == 1
    assert state.melds[0][0]["type"] == 2
    assert state.melds[0][0]["tiles"][-1] == "0m"
    assert state.melds[0][0]["froms"] == [1, 0, 0, 0]


@pytest.mark.parametrize("kind,hand", [(3, ["5m"]), (2, ["5m"]), (99, ["5m"]), (3, [])])
def test_invalid_kan_does_not_remove_tiles(kind, hand):
    state = GameState(0)
    state.apply(event("ActionNewRound", {"tiles": hand}, 0))
    state.apply(event("ActionAnGangAddGang", {"seat": 0, "type": kind, "tiles": "5m"}, 1))
    assert state.hand == hand
    assert state.status == "incomplete"
    assert not state.melds[0]


def snapshot():
    return {"chang": 0, "ju": 1, "ben": 2, "liqibang": 1, "index_player": 0,
            "hands": ["0m", "1p"], "doras": ["4s"], "left_tile_count": 30,
            "players": [{"score": 25000, "liqiposition": -1, "tilenum": 2,
                         "qipais": ["1m"], "mings": []},
                        {"score": 24000, "liqiposition": 1, "tilenum": 10,
                         "qipais": ["9p"], "mings": [{"type": 1, "tile": ["5s"] * 3, "from": [0, 1, 1]}]},
                        {"score": 25000, "qipais": [], "mings": []},
                        {"score": 25000, "qipais": [], "mings": []}]}


def test_snapshot_replaces_old_state_then_accepts_tail_action():
    state = GameState(0)
    state.invalidate("Old capture gap")
    state.restore(snapshot(), next_step=42)
    state.apply(event("ActionDiscardTile", {"seat": 0, "tile": "0m"}, 42))
    assert state.status == "tracking"
    assert state.hand == ["1p"]
    assert state.scores == [25000, 24000, 25000, 25000]
    assert state.round["liqibang"] == 1
    assert state.discards[0][0]["tsumogiri"] is None
    assert state.discards[0][-1]["tile"] == "0m"
    assert state.player_metadata[1]["riichi_position"] == 1


def test_snapshot_only_accepts_first_live_step_then_enforces_gaps():
    state = GameState(0)
    state.restore(snapshot())
    state.apply(event("ActionDealTile", {"seat": 1, "tile": ""}, 100))
    assert state.status == "tracking"
    state.apply(event("ActionDiscardTile", {"seat": 1, "tile": "9s"}, 102))
    assert state.status == "incomplete"


def test_incomplete_snapshot_and_unknown_seat_are_flagged():
    state = GameState()
    state.restore({"players": []})
    assert state.status == "incomplete"
    assert "Own seat is unknown" in state.issues
    state = GameState(0)
    value = snapshot()
    value["players"][0]["qipais"] = ["1m?"]
    state.restore(value)
    assert state.status == "incomplete"


def test_duplicate_round_start_cannot_erase_current_hand():
    state = GameState(0)
    start = event("ActionNewRound", {"tiles": ["1m"]}, 0)
    state.apply(start)
    assert state.apply(start) is False
    assert state.hand == ["1m"]


def test_snapshot_response_flows_through_capture_writer(tmp_path):
    document = schema().document
    nodes = document["nested"]["lq"]["nested"]
    nodes["GameSnapshot"] = {"fields": {
        "hands": {"id": 6, "type": "string", "rule": "repeated"},
        "players": {"id": 9, "type": "Player", "rule": "repeated"}},
        "nested": {"Player": {"fields": {"score": {"id": 1, "type": "int32"}}}}}
    nodes["GameRestore"]["fields"]["snapshot"] = {"id": 1, "type": "GameSnapshot"}
    writer = CaptureWriter(tmp_path / "capture.jsonl", LiqiSchema(document), seat=0)
    def record(frame, client=False):
        return writer.record(connection="a", host="example", content=frame,
                             from_client=client, timestamp=1)
    record(wrapper(2, ".lq.FastTest.syncGame", b""), True)
    snap = blob(6, b"5m") + blob(9, b"") * 4
    tail = action("ActionDiscardTile", blob(2, b"5m"), step=20, encoded=False)
    restored = blob(1, blob(1, snap) + blob(2, tail))
    result = record(wrapper(3, "", restored))
    assert result["state"]["hand"] == []
    assert result["state"]["step"] == 20
    assert result["state"]["status"] == "tracking"
