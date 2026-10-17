from copy import deepcopy
import json
import os
import pytest

from agents.mahjong_soul.policy import BaselinePolicy
from agents.mahjong_soul.shadow import ShadowFollower
from tests.mahjong_soul.test_input import inputs


class Reader:
    def __init__(self, schema):
        self.report, _ = inputs()
        self.report["connection_open"] = False; self.report["state_ready"] = False
    def consume(self, row):
        if row.get("fault"): raise ValueError("Malformed row")
        if "report" in row: self.report = deepcopy(row["report"])
        if row.get("event") == "connection_closed":
            self.report["connection_open"] = False; self.report["state_ready"] = False
    def snapshot(self): return deepcopy(self.report)


def row(report=None, *, connection="game", timestamp=100):
    value = {"connection":connection,"direction":"server","raw_base64":"","timestamp":timestamp}
    if report is not None: value["report"] = deepcopy(report)
    return value


def append(path, value):
    with path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(value)+"\n")


def setup(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setattr("agents.mahjong_soul.shadow.GameReader", Reader)
    path = tmp_path / "capture-one.jsonl"
    report, _ = inputs(); append(path, row(report))
    follower = ShadowFollower(None, file=path, wall_clock=lambda:100, clock=lambda:1, **kwargs)
    assert follower.poll()["reason"] == "capture_bootstrapped"
    return path, report, follower


def advance(report):
    report = deepcopy(report); report["state"]["step"] += 1
    return report


def test_bootstrap_does_not_propose_and_new_board_is_suggested_once(tmp_path, monkeypatch):
    path, report, follower = setup(tmp_path, monkeypatch)
    assert follower.poll()["reason"] == "board_already_considered"
    append(path, row(advance(report)))
    result = follower.poll()
    assert result["kind"] == "suggestion" and result["action"] == {"kind":"discard","tile":"0p"}
    assert result["executable"] is False and "hand" not in json.dumps(result)
    assert follower.poll()["reason"] == "board_already_considered"
    append(path, row())
    assert follower.poll()["reason"] == "board_already_considered"


def test_lobby_activity_and_file_mtime_do_not_make_old_game_state_fresh(tmp_path, monkeypatch):
    path, report, follower = setup(tmp_path, monkeypatch)
    append(path, row(advance(report), timestamp=90))
    append(path, row(connection="lobby", timestamp=100))
    assert follower.poll()["reason"] == "stale_game_capture"
    append(path, row(timestamp=100))
    assert follower.poll()["kind"] == "suggestion"


def test_connection_close_and_reauthentication_are_not_previous_board(tmp_path, monkeypatch):
    path, report, follower = setup(tmp_path, monkeypatch)
    append(path, {"event":"connection_closed","connection":"game"})
    assert follower.poll()["reason"] == "waiting_for_game_connection"
    report["game_generation"] += 1
    append(path, row(report))
    assert follower.poll()["kind"] == "suggestion"


def test_partial_row_waits_and_malformed_capture_blocks_until_truncation(tmp_path, monkeypatch):
    path, report, follower = setup(tmp_path, monkeypatch)
    encoded = json.dumps(row(advance(report)))
    with path.open("a", encoding="utf-8") as stream: stream.write(encoded[:-10])
    assert follower.poll()["reason"] == "waiting_for_complete_row"
    with path.open("a", encoding="utf-8") as stream: stream.write(encoded[-10:]+"\n")
    assert follower.poll()["kind"] == "suggestion"
    with path.open("a", encoding="utf-8") as stream: stream.write("bad json\n")
    assert follower.poll()["reason"] == "malformed_capture_blocked"
    append(path, row(advance(advance(report))))
    assert follower.poll()["reason"] == "malformed_capture_blocked"
    path.write_text("", encoding="utf-8")
    assert follower.poll()["reason"] == "capture_reset_bootstrapped"
    append(path, row(advance(advance(advance(report)))))
    assert follower.poll()["kind"] == "suggestion"


def test_file_rotation_bootstraps_history_without_restarting_policy(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.mahjong_soul.shadow.GameReader", Reader)
    report, _ = inputs(); first = tmp_path / "capture-first.jsonl"; append(first, row(report))
    follower = ShadowFollower(None, directory=tmp_path, wall_clock=lambda:100)
    policy = follower.policy
    follower.poll()
    second = tmp_path / "capture-second.jsonl"; append(second, row(advance(report)))
    os.utime(second, (first.stat().st_mtime+10, first.stat().st_mtime+10))
    assert follower.poll()["reason"] == "capture_bootstrapped"
    assert follower.poll()["reason"] == "board_already_considered"
    assert follower.policy is policy


@pytest.mark.parametrize("failure", ["policy_crash","board_changes","capture_stales","slow_policy"])
def test_failed_decision_does_not_emit_or_repeat_policy_on_same_board(tmp_path, monkeypatch, failure):
    path, report, follower = setup(tmp_path, monkeypatch)
    new = advance(report); calls = []
    class Policy:
        def choose(self, request):
            calls.append(request["board_token"])
            if failure == "policy_crash": raise RuntimeError("bad policy")
            if failure == "board_changes": append(path, row(advance(new)))
            if failure == "capture_stales": follower.wall_clock = lambda:105
            return BaselinePolicy().choose(request)
    follower.policy = Policy()
    if failure == "slow_policy":
        values = iter([1,4]); follower.clock = lambda:next(values)
    append(path, row(new))
    result = follower.poll()
    assert result["reason"] == "decision_rejected" and result["executable"] is False
    if failure != "board_changes":
        follower.poll()
        assert len(calls) == 1


@pytest.mark.parametrize("stamp", [None,False,float("inf"),101,90])
def test_invalid_or_out_of_range_frame_timestamp_does_not_authorize_suggestion(tmp_path, monkeypatch, stamp):
    path, report, follower = setup(tmp_path, monkeypatch)
    follower.frame_times.clear()
    append(path, row(advance(report), timestamp=stamp))
    assert follower.poll()["reason"] == "stale_game_capture"


@pytest.mark.parametrize("action,expected", [
    ({"kind":"discard","tile":"1m"},"Discard 1 Man"),
    ({"kind":"discard","tile":"2p"},"Discard 2 Pin"),
    ({"kind":"discard","tile":"3s"},"Discard 3 Sou"),
    ({"kind":"discard","tile":"0p"},"Discard Red 5 Pin"),
    ({"kind":"discard","tile":"2z"},"Discard South Wind"),
    ({"kind":"riichi","tile":"6p"},"Riichi, then discard 6 Pin"),
    ({"kind":"chi","combination":"1m|2m","called_tile":"3m"},"Chi 1 Man + 2 Man with 3 Man"),
])
def test_readable_recommendations_use_requested_tile_names(action,expected):
    from agents.mahjong_soul.shadow import format_suggestion
    assert format_suggestion({"action":action}) == expected
