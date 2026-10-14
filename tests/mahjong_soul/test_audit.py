from games.mahjong_soul.live.runtime.audit import audit
from tests.mahjong_soul.test_decoder_state import action, blob, schema, wrapper
from tests.mahjong_soul.test_reader_monitor import record, event
from games.mahjong_soul.live.runtime.state import GameState


def test_audit_distinguishes_duplicate_restore_steps_from_gaps():
    start = record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m"))))
    discard = record(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", blob(2, b"1m"), step=1)))
    result = audit([start, discard, discard], schema(), seat=0)
    assert result["coherent"]
    assert result["rounds"][0]["duplicates"] == 1
    assert result["rounds"][0]["actions"] == 2
    assert result["rounds"][0]["gaps"] == []
    gap = record(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", blob(2, b"1m"), step=2)))
    result = audit([start, gap], schema(), seat=0)
    assert not result["coherent"]
    assert result["rounds"][0]["gaps"] == [1]


def test_audit_reports_conflicting_same_step():
    start = record(wrapper(1, ".lq.ActionPrototype", action("ActionNewRound", blob(4, b"1m"))))
    first = record(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", blob(2, b"1m"), step=1)))
    second = record(wrapper(1, ".lq.ActionPrototype", action("ActionDiscardTile", blob(2, b"2m"), step=1)))
    assert audit([start, first, second], schema(), seat=0)["rounds"][0]["conflicts"] == [1]


def test_win_clears_awarded_riichi_sticks():
    state = GameState(0)
    state.apply(event("ActionNewRound", {"scores": [25000] * 4, "tiles": ["1m"], "liqibang": 2}, 0))
    state.apply(event("ActionHule", {"scores": [29000, 23000, 24000, 26000]}, 1))
    assert state.round["liqibang"] == 0
    assert state.status == "round_ended"
