from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import _normalize_card
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _CardDecoder:
    def __init__(self):
        self.tables = {
            100: {
                "base": _lua("table", 200),
                "ability": _lua("table", 300),
                "config": _lua("table", 400),
                "playing_card": _lua("integer", 17),
                "debuff": _lua("boolean", False),
            },
            200: {
                "value": _lua("string", "Ace"),
                "suit": _lua("string", "Spades"),
            },
            300: {
                "forced_selection": _lua("boolean", True),
                "perma_bonus": _lua("integer", 0),
            },
            400: {"center": _lua("table", 500)},
            500: {
                "key": _lua("string", "c_base"),
                "name": _lua("string", "Base Card"),
            },
        }

    def string_fields(self, address):
        return dict(self.tables.get(int(address), {}))


def test_live_card_normalizer_exposes_cerulean_forced_selection():
    normalized = _normalize_card(_CardDecoder(), 100)

    assert normalized["live_id"] == 17
    assert normalized["forced_selection"] is True


def test_translator_hydrates_cerulean_forced_selection_on_hand_card():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {
                "count": 2,
                "limit": 2,
                "cards": [
                    {
                        "value": {"rank": "Ace", "suit": "Spades"},
                        "live_id": 17,
                        "forced_selection": True,
                    },
                    {
                        "value": {"rank": "King", "suit": "Hearts"},
                        "live_id": 18,
                        "forced_selection": False,
                    },
                ],
            },
            "cards": {"count": 0, "limit": 0, "cards": []},
            "jokers": {"count": 0, "limit": 5, "cards": []},
            "consumables": {"count": 0, "limit": 2, "cards": []},
            "blind": {
                "type": "BOSS",
                "name": "Cerulean Bell",
                "chips": 100000,
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.boss_name == "Cerulean Bell"
    assert state.hand[0].forced_selection is True
    assert state.hand[1].forced_selection is False
