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


def _number(value):
    return LuaValue("number", float(value), 0)


def _string(value):
    return LuaValue("string", value, 0)


def _snapshot_payload(game_fields):
    game_address = 100
    decoder = _FakeDecoder({game_address: game_fields})
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


def test_env_r2_live_observer_exposes_hone_edition_rate():
    payload = _snapshot_payload({"edition_rate": _number(2.0)})

    assert payload["joker_generation_edition_rate"] == 2.0


def test_env_r2_live_observer_exposes_glow_up_edition_rate_from_integer_tvalue():
    payload = _snapshot_payload({"edition_rate": _integer(4)})

    assert payload["joker_generation_edition_rate"] == 4.0


def test_env_r2_live_observer_omits_non_numeric_edition_rate():
    payload = _snapshot_payload({"edition_rate": _string("2")})

    assert "joker_generation_edition_rate" not in payload


def test_env_r2_live_observer_omits_missing_edition_rate():
    payload = _snapshot_payload({})

    assert "joker_generation_edition_rate" not in payload


def test_env_r2_translator_maps_live_edition_rate():
    state = _translate({"joker_generation_edition_rate": 4.0})

    assert state.joker_generation_edition_rate == 4.0


def test_env_r2_translator_retains_base_default_when_live_rate_is_unavailable():
    state = _translate({})

    assert state.joker_generation_edition_rate == 1.0
