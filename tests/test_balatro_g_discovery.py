from games.balatro.live.external.balatro_g_discovery import discover_balatro_g_table
from games.balatro.live.external.luajit_memory import LuaJITMemoryError, LuaValue


class _Decoder:
    def __init__(self, *, tied=False):
        self._strings = (0x1000,)
        self._nodes = {0x1000: (0x2000, 0x2100) if tied else (0x2000, 0x2100)}
        self._values = {
            0x2000: LuaValue("table", 0x3000, 0),
            0x2100: LuaValue("table", 0x4000, 0),
        }
        self._fields = {
            0x3000: {
                "GAME": LuaValue("table", 0x5000, 0),
                "STATE": LuaValue("integer", 6, 0),
                "STATES": LuaValue("table", 0x5100, 0),
                "hand": LuaValue("table", 0x5200, 0),
                "jokers": LuaValue("table", 0x5300, 0),
                "consumeables": LuaValue("table", 0x5400, 0),
                "deck": LuaValue("table", 0x5500, 0),
            },
            0x4000: {
                "GAME": LuaValue("table", 0x6000, 0),
                "STATE": LuaValue("integer", 6, 0),
                "hand": LuaValue("table", 0x6200, 0),
                "jokers": LuaValue("table", 0x6300, 0),
            },
            0x5000: {
                "current_round": LuaValue("table", 0x7000, 0),
                "round_resets": LuaValue("table", 0x7100, 0),
                "dollars": LuaValue("integer", 12, 0),
            },
            0x6000: {},
            0x5200: {"cards": LuaValue("table", 0x7200, 0)},
            0x5300: {"cards": LuaValue("table", 0x7300, 0)},
            0x5400: {"cards": LuaValue("table", 0x7400, 0)},
            0x5500: {"cards": LuaValue("table", 0x7500, 0)},
            0x6200: {"cards": LuaValue("table", 0x7600, 0)},
            0x6300: {"cards": LuaValue("table", 0x7700, 0)},
        }
        if tied:
            self._fields[0x4000] = dict(self._fields[0x3000])
            self._fields[0x6000] = dict(self._fields[0x5000])
            self._fields[0x4000]["GAME"] = LuaValue("table", 0x6000, 0)

    def find_gc_strings(self, text, *, max_matches=256):
        assert text == "G"
        return self._strings

    def find_key_nodes_for_string(self, string_address):
        return self._nodes[string_address]

    def read_value_at(self, address):
        return self._values[address]

    def string_fields(self, table):
        return self._fields.get(table, {})


class _FallbackDecoder:
    def __init__(self, *, tied=False):
        self._values = {
            0x2200: LuaValue("table", 0x5000, 0),
        }
        self._owners = (0x3000, 0x4000) if tied else (0x3000, 0x4000)
        self._fields = {
            0x3000: {
                "GAME": LuaValue("table", 0x5000, 0),
                "STATE": LuaValue("integer", 6, 0),
                "STATES": LuaValue("table", 0x5100, 0),
                "hand": LuaValue("table", 0x5200, 0),
                "jokers": LuaValue("table", 0x5300, 0),
                "consumeables": LuaValue("table", 0x5400, 0),
                "deck": LuaValue("table", 0x5500, 0),
            },
            0x4000: {
                "GAME": LuaValue("table", 0x6000, 0),
                "STATE": LuaValue("integer", 6, 0),
                "hand": LuaValue("table", 0x6200, 0),
                "jokers": LuaValue("table", 0x6300, 0),
            },
            0x5000: {
                "current_round": LuaValue("table", 0x7000, 0),
                "round_resets": LuaValue("table", 0x7100, 0),
                "dollars": LuaValue("integer", 12, 0),
            },
            0x6000: {},
            0x5200: {"cards": LuaValue("table", 0x7200, 0)},
            0x5300: {"cards": LuaValue("table", 0x7300, 0)},
            0x5400: {"cards": LuaValue("table", 0x7400, 0)},
            0x5500: {"cards": LuaValue("table", 0x7500, 0)},
            0x6200: {"cards": LuaValue("table", 0x7600, 0)},
            0x6300: {"cards": LuaValue("table", 0x7700, 0)},
        }
        if tied:
            self._fields[0x4000] = dict(self._fields[0x3000])
            self._fields[0x6000] = dict(self._fields[0x5000])
            self._fields[0x4000]["GAME"] = LuaValue("table", 0x6000, 0)

    def find_gc_strings(self, text, *, max_matches=256):
        if text == "G":
            return ()
        assert text == "GAME"
        return (0x1100,)

    def find_key_nodes_for_string(self, string_address):
        assert string_address == 0x1100
        return (0x2200,)

    def read_value_at(self, address):
        return self._values[address]

    def find_table_owners_of_node(self, node):
        assert node == 0x2200
        return self._owners

    def string_fields(self, table):
        return self._fields.get(table, {})


def test_direct_global_binding_prefers_live_balatro_structure():
    decoder = _Decoder()
    assert discover_balatro_g_table(decoder) == 0x3000


def test_direct_global_binding_fails_closed_on_equal_candidates():
    decoder = _Decoder(tied=True)
    try:
        discover_balatro_g_table(decoder)
    except LuaJITMemoryError as error:
        assert "multiple equally strong" in str(error)
    else:
        raise AssertionError("expected ambiguous G discovery to fail closed")


def test_structural_game_owner_fallback_recovers_balatro_g():
    decoder = _FallbackDecoder()
    assert discover_balatro_g_table(decoder) == 0x3000


def test_structural_game_owner_fallback_fails_closed_on_equal_candidates():
    decoder = _FallbackDecoder(tied=True)
    try:
        discover_balatro_g_table(decoder)
    except LuaJITMemoryError as error:
        assert "multiple equally strong Balatro G GAME-owner candidates" in str(error)
    else:
        raise AssertionError("expected ambiguous fallback G discovery to fail closed")
