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
    decoder = _FakeDecoder({game_address: dict(game_fields)})
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


def test_env_r2_live_observer_exposes_authoritative_shop_pricing_state():
    payload = _snapshot_payload(
        {
            "inflation": _integer(2),
            "discount_percent": _integer(25),
        }
    )

    assert payload["shop_inflation_observed"] is True
    assert payload["shop_inflation"] == 2
    assert payload["shop_discount_percent_observed"] is True
    assert payload["shop_discount_percent"] == 25


def test_env_r2_live_observer_preserves_integral_lua_numbers_and_zero():
    payload = _snapshot_payload(
        {
            "inflation": _number(0.0),
            "discount_percent": _number(50.0),
        }
    )

    assert payload["shop_inflation_observed"] is True
    assert payload["shop_inflation"] == 0
    assert payload["shop_discount_percent_observed"] is True
    assert payload["shop_discount_percent"] == 50


def test_env_r2_live_observer_fails_closed_for_missing_or_invalid_pricing_state():
    payload = _snapshot_payload({})
    assert payload["shop_inflation_observed"] is False
    assert "shop_inflation" not in payload
    assert payload["shop_discount_percent_observed"] is False
    assert "shop_discount_percent" not in payload

    payload = _snapshot_payload(
        {
            "inflation": _number(1.5),
            "discount_percent": _number(25.5),
        }
    )
    assert payload["shop_inflation_observed"] is False
    assert "shop_inflation" not in payload
    assert payload["shop_discount_percent_observed"] is False
    assert "shop_discount_percent" not in payload

    payload = _snapshot_payload(
        {
            "inflation": _integer(-1),
            "discount_percent": _integer(101),
        }
    )
    assert payload["shop_inflation_observed"] is False
    assert payload["shop_discount_percent_observed"] is False


def test_env_r2_translator_maps_authoritative_shop_pricing_state():
    state = _translate(
        {
            "shop_inflation_observed": True,
            "shop_inflation": 3,
            "shop_discount_percent_observed": True,
            "shop_discount_percent": 50,
        }
    )

    assert state.shop_inflation_observed is True
    assert state.shop_inflation == 3
    assert state.shop_discount_percent_observed is True
    assert state.shop_discount_percent == 50


def test_env_r2_translator_preserves_authoritative_zero_pricing_state():
    state = _translate(
        {
            "shop_inflation_observed": True,
            "shop_inflation": 0,
            "shop_discount_percent_observed": True,
            "shop_discount_percent": 0,
        }
    )

    assert state.shop_inflation_observed is True
    assert state.shop_inflation == 0
    assert state.shop_discount_percent_observed is True
    assert state.shop_discount_percent == 0


def test_env_r2_translator_fails_closed_for_invalid_shop_pricing_state():
    invalid_inflation = (True, "2", 2.0, -1, None)
    for value in invalid_inflation:
        state = _translate(
            {
                "shop_inflation_observed": True,
                "shop_inflation": value,
            }
        )
        assert state.shop_inflation_observed is False
        assert state.shop_inflation == 0

    invalid_discount = (True, "25", 25.0, -1, 101, None)
    for value in invalid_discount:
        state = _translate(
            {
                "shop_discount_percent_observed": True,
                "shop_discount_percent": value,
            }
        )
        assert state.shop_discount_percent_observed is False
        assert state.shop_discount_percent == 0
