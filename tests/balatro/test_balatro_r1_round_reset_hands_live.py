from games.balatro.live import DefaultBalatroStateTranslator, LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _string(value):
    return LuaValue("string", value, 0)


def _snapshot_payload(round_resets):
    game_address = 100
    round_resets_address = 101
    decoder = _FakeDecoder(
        {
            game_address: {"round_resets": _table(round_resets_address)},
            round_resets_address: round_resets,
        }
    )
    payload, _, _ = snapshot_payload_from_live_memory(
        decoder,
        {"GAME": _table(game_address)},
    )
    return payload


def _translate(payload):
    return DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=1,
            phase="SHOP",
            state_complete=True,
            payload=payload,
        )
    )


def test_live_observer_exposes_observed_next_round_hands():
    payload = _snapshot_payload({"hands": _integer(4)})

    assert payload["round_reset_hands_observed"] is True
    assert payload["round_reset_hands"] == 4


def test_live_observer_preserves_observed_zero_next_round_hands():
    payload = _snapshot_payload({"hands": _integer(0)})

    assert payload["round_reset_hands_observed"] is True
    assert payload["round_reset_hands"] == 0


def test_live_observer_fails_closed_when_next_round_hands_is_missing():
    payload = _snapshot_payload({})

    assert payload["round_reset_hands_observed"] is False
    assert "round_reset_hands" not in payload


def test_live_observer_fails_closed_when_next_round_hands_is_not_numeric():
    payload = _snapshot_payload({"hands": _string("4")})

    assert payload["round_reset_hands_observed"] is False
    assert "round_reset_hands" not in payload


def test_translator_maps_observed_next_round_hands():
    state = _translate(
        {
            "round_reset_hands_observed": True,
            "round_reset_hands": 4,
        }
    )

    assert state.round_reset_hands_observed is True
    assert state.round_reset_hands == 4


def test_translator_preserves_observed_zero_next_round_hands():
    state = _translate(
        {
            "round_reset_hands_observed": True,
            "round_reset_hands": 0,
        }
    )

    assert state.round_reset_hands_observed is True
    assert state.round_reset_hands == 0


def test_translator_fails_closed_when_next_round_hands_is_missing():
    state = _translate({})

    assert state.round_reset_hands_observed is False
    assert state.round_reset_hands == 0


def test_translator_fails_closed_for_invalid_observed_next_round_hands():
    for invalid_value in (True, "4", 4.0, -1, None):
        state = _translate(
            {
                "round_reset_hands_observed": True,
                "round_reset_hands": invalid_value,
            }
        )

        assert state.round_reset_hands_observed is False
        assert state.round_reset_hands == 0
