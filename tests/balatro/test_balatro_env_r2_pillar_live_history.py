from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import _normalize_card
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

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


def _decoder_for_card(*, ability_fields=None, include_ability=True):
    CARD = 100
    BASE = 101
    ABILITY = 102
    CONFIG = 103
    CENTER = 104
    card = {
        "base": _table(BASE),
        "config": _table(CONFIG),
        "playing_card": _integer(17),
        "debuff": _boolean(False),
    }
    if include_ability:
        card["ability"] = _table(ABILITY)
    tables = {
        CARD: card,
        BASE: {"value": _string("A"), "suit": _string("Spades")},
        CONFIG: {"center": _table(CENTER)},
        CENTER: {"key": _string("c_base")},
    }
    if include_ability:
        tables[ABILITY] = dict(ability_fields or {})
    return _FakeDecoder(tables), CARD


def _owned_record(**history):
    return {
        "value": {"rank": "A", "suit": "Spades"},
        "modifier": {},
        "live_id": 17,
        "debuff": False,
        "permanent_bonus": 0,
        "forced_selection": False,
        **history,
    }


def _snapshot(record):
    return LiveBalatroSnapshot(
        sequence=1,
        phase="BLIND_SELECT",
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "owned_cards": {"count": 1, "limit": 1, "cards": [record]},
        },
    )


def test_live_memory_card_observes_true_played_this_ante():
    decoder, card_address = _decoder_for_card(
        ability_fields={"played_this_ante": _boolean(True)}
    )

    card = _normalize_card(decoder, card_address)

    assert card["played_this_ante_observed"] is True
    assert card["played_this_ante"] is True


def test_live_memory_card_observes_missing_ability_key_as_false():
    decoder, card_address = _decoder_for_card(ability_fields={})

    card = _normalize_card(decoder, card_address)

    assert card["played_this_ante_observed"] is True
    assert card["played_this_ante"] is False


def test_live_memory_card_keeps_missing_ability_table_unobserved():
    decoder, card_address = _decoder_for_card(include_ability=False)

    card = _normalize_card(decoder, card_address)

    assert "played_this_ante_observed" not in card
    assert "played_this_ante" not in card


def test_translator_preserves_authoritative_true_played_this_ante():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(
            _owned_record(
                played_this_ante_observed=True,
                played_this_ante=True,
            )
        )
    )

    assert state.owned_deck is not None
    assert len(state.owned_deck) == 1
    card = state.owned_deck[0]
    assert card.played_this_ante_observed is True
    assert card.played_this_ante is True


def test_translator_preserves_authoritative_false_played_this_ante():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(
            _owned_record(
                played_this_ante_observed=True,
                played_this_ante=False,
            )
        )
    )

    assert state.owned_deck is not None
    card = state.owned_deck[0]
    assert card.played_this_ante_observed is True
    assert card.played_this_ante is False


def test_translator_keeps_unobserved_history_distinct_from_false():
    state = DefaultBalatroStateTranslator().translate(_snapshot(_owned_record()))

    assert state.owned_deck is not None
    card = state.owned_deck[0]
    assert card.played_this_ante_observed is False
    assert card.played_this_ante is False


def test_strict_owned_deck_rejects_history_without_observation_marker():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(_owned_record(played_this_ante=True))
    )

    assert state.owned_deck is None


def test_strict_owned_deck_rejects_malformed_history_marker_or_value():
    translator = DefaultBalatroStateTranslator()

    state = translator.translate(
        _snapshot(
            _owned_record(
                played_this_ante_observed="yes",
                played_this_ante=True,
            )
        )
    )
    assert state.owned_deck is None

    state = translator.translate(
        _snapshot(
            _owned_record(
                played_this_ante_observed=True,
                played_this_ante=1,
            )
        )
    )
    assert state.owned_deck is None
