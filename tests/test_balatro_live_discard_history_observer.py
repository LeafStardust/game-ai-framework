from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _number(value):
    return LuaValue("number", float(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _snapshot(*, discards_used=1):
    GAME = 100
    CURRENT_ROUND = 101
    ROUND_RESETS = 102
    BLIND = 103
    STATES = 104

    current_round = {
        "hands_left": _integer(3),
        "discards_left": _integer(2),
    }
    if discards_used is not None:
        current_round["discards_used"] = _integer(discards_used)

    decoder = _FakeDecoder(
        {
            GAME: {
                "dollars": _integer(7),
                "round": _integer(2),
                "chips": _integer(100),
                "stake": _integer(1),
                "current_round": _table(CURRENT_ROUND),
                "round_resets": _table(ROUND_RESETS),
                "blind": _table(BLIND),
                "blind_on_deck": _string("Small"),
                "facing_blind": _boolean(True),
            },
            CURRENT_ROUND: current_round,
            ROUND_RESETS: {"ante": _integer(1)},
            BLIND: {
                "chips": _integer(300),
                "name": _string("Small Blind"),
                "boss": _boolean(False),
            },
            STATES: {"SELECTING_HAND": _number(1)},
        }
    )
    root = {
        "GAME": _table(GAME),
        "STATE": _number(1),
        "STATE_COMPLETE": _boolean(True),
        "STATES": _table(STATES),
    }
    return snapshot_payload_from_live_memory(decoder, root)


def _translate(payload, phase, state_complete):
    return DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=1,
            phase=phase,
            state_complete=state_complete,
            payload=payload,
        )
    )


def test_process_memory_snapshot_exposes_current_round_discards_used():
    payload, phase, state_complete = _snapshot(discards_used=1)

    assert phase == "SELECTING_HAND"
    assert state_complete is True
    assert payload["round"]["discards_left"] == 2
    assert payload["round"]["discards_used"] == 1

    state = _translate(payload, phase, state_complete)
    assert state.discards_remaining == 2
    assert state.discards_used == 1


def test_missing_live_discard_history_stays_unobserved_instead_of_guessing_zero():
    payload, phase, state_complete = _snapshot(discards_used=None)

    assert "discards_used" not in payload["round"]

    state = _translate(payload, phase, state_complete)
    assert state.discards_used is None
