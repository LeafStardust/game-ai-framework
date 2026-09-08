import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.live.runtime.live_memory_observer import _normalize_card
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


class _Decoder:
    def __init__(self):
        self.tables = {
            1: {
                "base": LuaValue("table", 2, 0),
                "ability": LuaValue("table", 3, 0),
                "config": LuaValue("table", 4, 0),
            },
            2: {
                "value": LuaValue("string", "A", 0),
                "suit": LuaValue("string", "Spades", 0),
            },
            3: {
                "forced_selection": LuaValue("boolean", True, 0),
            },
            4: {},
        }

    def string_fields(self, address):
        return self.tables.get(address, {})


def test_native_memory_card_normalization_exposes_forced_selection():
    normalized = _normalize_card(_Decoder(), 1)

    assert normalized["forced_selection"] is True


def test_native_translator_hydrates_forced_selection():
    card = DefaultBalatroStateTranslator()._card(
        {
            "value": {"rank": "A", "suit": "Spades"},
            "forced_selection": True,
        },
        live_id=7,
    )

    assert card.forced_selection is True


def test_production_stack_does_not_install_cerulean_overlay():
    assert not hasattr(
        DefaultBalatroStateTranslator,
        "_cerulean_live_state_installed",
    )
