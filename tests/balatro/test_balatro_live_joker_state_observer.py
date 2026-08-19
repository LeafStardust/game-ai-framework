from games.balatro.live.external.live_memory_observer import (
    _normalize_public_item_state,
    _normalize_round_joker_public_state,
)
from games.balatro.live.external.luajit_memory import LuaValue


class _FakeDecoder:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def string_fields(self, address):
        return self.tables[address]


def _table(address):
    return LuaValue("table", address, 0)


def _number(value):
    return LuaValue("number", float(value), 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _string(value):
    return LuaValue("string", value, 0)


def test_declared_joker_state_reads_direct_and_nested_ability_counters():
    EXTRA = 100
    decoder = _FakeDecoder({EXTRA: {"chips": _integer(45)}})

    green = _normalize_public_item_state(
        decoder,
        "j_green_joker",
        "Green Joker",
        "Green Joker",
        {"mult": _integer(12)},
        {},
    )
    runner = _normalize_public_item_state(
        decoder,
        "j_runner",
        "Runner",
        "Runner",
        {"extra": _table(EXTRA)},
        {},
    )

    assert green == {"mult": 12}
    assert runner == {"chips": 45}


def test_declared_joker_state_reads_scalar_extra_and_explicit_card_alias():
    decoder = _FakeDecoder()

    seltzer = _normalize_public_item_state(
        decoder,
        "j_seltzer",
        "Seltzer",
        "Seltzer",
        {"extra": _integer(7)},
        {},
    )
    egg = _normalize_public_item_state(
        decoder,
        "j_egg",
        "Egg",
        "Egg",
        {},
        {"sell_cost": _integer(15)},
    )

    assert seltzer == {"rounds_remaining": 7}
    assert egg == {"sell_value": 15}


def test_undeclared_ability_fields_do_not_leak_into_public_state():
    decoder = _FakeDecoder()

    result = _normalize_public_item_state(
        decoder,
        "j_acrobat",
        "Acrobat",
        "Acrobat",
        {
            "mult": _integer(99),
            "x_mult": _number(99),
            "secret_counter": _integer(123),
        },
        {},
    )

    assert result == {}


def test_round_joker_state_includes_ancient_castle_and_idol_targets():
    ANCIENT = 200
    CASTLE = 201
    IDOL = 202
    decoder = _FakeDecoder(
        {
            ANCIENT: {"suit": _string("Clubs")},
            CASTLE: {"suit": _string("Hearts")},
            IDOL: {"rank": _string("Ace"), "suit": _string("Spades")},
        }
    )

    result = _normalize_round_joker_public_state(
        decoder,
        {
            "ancient_card": _table(ANCIENT),
            "castle_card": _table(CASTLE),
            "idol_card": _table(IDOL),
        },
    )

    assert result["j_ancient"] == {"suit": "Clubs"}
    assert result["j_castle"] == {"suit": "Hearts"}
    assert result["j_idol"] == {"rank": "Ace", "suit": "Spades"}
