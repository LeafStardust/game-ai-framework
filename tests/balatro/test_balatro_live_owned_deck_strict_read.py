from games.balatro.live.external.live_memory_observer import _normalize_card_array
from games.balatro.live.external.luajit_memory import LuaJITMemoryError, LuaValue


class _StrictDecoder:
    def __init__(self, *, fail_array=False):
        self.fail_array = fail_array
        self.tables = {
            10: {
                "base": LuaValue("table", 11, 0),
                "config": LuaValue("table", 12, 0),
                "playing_card": LuaValue("integer", 7, 0),
            },
            11: {
                "value": LuaValue("string", "Ace", 0),
                "suit": LuaValue("string", "Spades", 0),
            },
            12: {"center": LuaValue("table", 13, 0)},
            13: {"key": LuaValue("string", "c_base", 0)},
        }

    def array_items_strict(self, address):
        if self.fail_array:
            raise LuaJITMemoryError("simulated unreadable TValue")
        return ((0, LuaValue("table", 10, 0)),)

    def string_fields(self, address):
        return self.tables[address]


def test_balatro_env_r1_owned_deck_memory_read_is_all_or_nothing():
    cards = LuaValue("table", 1, 0)

    assert _normalize_card_array(_StrictDecoder(fail_array=True), cards) is None


def test_balatro_env_r1_owned_deck_memory_read_preserves_complete_collection():
    cards = LuaValue("table", 1, 0)

    result = _normalize_card_array(_StrictDecoder(), cards)

    assert result is not None
    assert result["count"] == 1
    assert result["limit"] == 1
    assert result["cards"][0]["live_id"] == 7
    assert result["cards"][0]["value"] == {"rank": "Ace", "suit": "Spades"}
