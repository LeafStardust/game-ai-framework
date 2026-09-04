from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import _normalize_card
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables.get(address, {})


def _v(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


def _card_decoder(facing=None):
    card = {
        "base": _v("table", 10),
        "ability": _v("table", 11),
        "config": _v("table", 12),
        "playing_card": _v("integer", 7),
    }
    if facing is not None:
        card["facing"] = facing
    return _Decoder(
        {
            1: card,
            10: {
                "value": _v("string", "A"),
                "suit": _v("string", "Spades"),
            },
            11: {},
            12: {"center": _v("table", 13)},
            13: {},
        }
    )


def _snapshot(facing_marker=...):
    card = {
        "value": {"rank": "A", "suit": "Spades"},
        "live_id": 7,
    }
    if facing_marker is not ...:
        card["facing"] = facing_marker
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "hand": {"count": 1, "limit": 8, "cards": [card]},
            "cards": {"count": 0, "limit": 0, "cards": []},
        },
    )


def test_r2_live_memory_card_exposes_only_exact_front_back_facing():
    back = _normalize_card(_card_decoder(_v("string", "back")), 1)
    front = _normalize_card(_card_decoder(_v("string", "front")), 1)
    missing = _normalize_card(_card_decoder(), 1)
    malformed = _normalize_card(_card_decoder(_v("string", "BACK")), 1)
    wrong_type = _normalize_card(_card_decoder(_v("boolean", True)), 1)

    assert back["facing"] == "back"
    assert front["facing"] == "front"
    assert "facing" not in missing
    assert "facing" not in malformed
    assert "facing" not in wrong_type


def test_r2_translator_marks_back_and_front_as_authoritatively_observed():
    translator = DefaultBalatroStateTranslator()

    back = translator.translate(_snapshot("back")).hand[0]
    front = translator.translate(_snapshot("front")).hand[0]

    assert back.face_down is True
    assert back.facing_observed is True
    assert front.face_down is False
    assert front.facing_observed is True


def test_r2_translator_fails_closed_for_missing_or_malformed_facing():
    translator = DefaultBalatroStateTranslator()

    missing = translator.translate(_snapshot()).hand[0]
    malformed = translator.translate(_snapshot("BACK")).hand[0]
    wrong_type = translator.translate(_snapshot(True)).hand[0]

    for card in (missing, malformed, wrong_type):
        assert card.face_down is False
        assert card.facing_observed is False
