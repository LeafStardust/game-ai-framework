from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import _normalize_blind
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


class _FakeDecoder:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def string_fields(self, address):
        return self.tables[address]


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def test_live_observer_whitelists_eye_accepted_hand_types():
    HANDS = 100
    decoder = _FakeDecoder(
        {
            HANDS: {
                "High Card": _boolean(True),
                "Pair": _boolean(False),
                "Flush": _boolean(True),
            }
        }
    )
    blind = {
        "boss": _boolean(True),
        "name": _string("The Eye"),
        "chips": _integer(1200),
        "hands": _table(HANDS),
    }
    game = {
        "blind_on_deck": _string("Boss"),
        "facing_blind": _boolean(True),
    }

    normalized = _normalize_blind(decoder, blind, game)

    assert normalized["type"] == "BOSS"
    assert normalized["name"] == "The Eye"
    assert normalized["hands"] == ["Flush", "High Card"]
    assert "only_hand" not in normalized


def test_live_observer_preserves_mouth_only_hand_key_when_not_set_yet():
    decoder = _FakeDecoder()
    blind = {
        "boss": _boolean(True),
        "name": _string("The Mouth"),
        "chips": _integer(1200),
        "only_hand": _boolean(False),
    }
    game = {
        "blind_on_deck": _string("Boss"),
        "facing_blind": _boolean(True),
    }

    normalized = _normalize_blind(decoder, blind, game)

    assert "only_hand" in normalized
    assert normalized["only_hand"] is None


def test_live_observer_drops_stale_mouth_only_hand_from_other_bosses():
    decoder = _FakeDecoder()
    blind = {
        "boss": _boolean(True),
        "name": _string("The Wall"),
        "chips": _integer(80000),
        "only_hand": _string("Two Pair"),
    }
    game = {
        "blind_on_deck": _string("Boss"),
        "facing_blind": _boolean(True),
    }

    normalized = _normalize_blind(decoder, blind, game)

    assert normalized["name"] == "The Wall"
    assert "only_hand" not in normalized


def test_translator_canonicalizes_eye_blind_hand_history():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "blind": {
                "type": "BOSS",
                "status": "CURRENT",
                "name": "The Eye",
                "score": 1200,
                "hands": ["High Card", "Two Pair"],
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.boss_name == "The Eye"
    assert state.boss_blind_state_observed is True
    assert state.boss_blind_hands == {"HIGH_CARD", "TWO_PAIR"}
    assert state.boss_blind_only_hand is None


def test_translator_preserves_mouth_first_hand_state_and_canonicalizes_target():
    translator = DefaultBalatroStateTranslator()
    empty_snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "blind": {
                "type": "BOSS",
                "status": "CURRENT",
                "name": "The Mouth",
                "score": 1200,
                "only_hand": None,
            }
        },
    )
    fixed_snapshot = LiveBalatroSnapshot(
        sequence=2,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "blind": {
                "type": "BOSS",
                "status": "CURRENT",
                "name": "The Mouth",
                "score": 1200,
                "only_hand": "Straight Flush",
            }
        },
    )

    empty = translator.translate(empty_snapshot)
    fixed = translator.translate(fixed_snapshot)

    assert empty.boss_blind_state_observed is True
    assert empty.boss_blind_only_hand is None
    assert fixed.boss_blind_state_observed is True
    assert fixed.boss_blind_only_hand == "STRAIGHT_FLUSH"
