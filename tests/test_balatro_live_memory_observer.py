from games.balatro.live.external.live_memory_observer import (
    _normalize_hand_levels,
    _normalize_round_joker_public_state,
    snapshot_payload_from_live_memory,
)
from games.balatro.live.external.luajit_memory import LuaValue


class _FakeDecoder:
    def __init__(self, tables, arrays):
        self.tables = tables
        self.arrays = arrays

    def string_fields(self, address):
        return self.tables[address]

    def array_items(self, address):
        return tuple(enumerate(self.arrays.get(address, [])))


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _number(value):
    return LuaValue("number", float(value), 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _card_tables(base_address, *, rank, suit, live_id):
    card = base_address
    base = base_address + 1
    config = base_address + 2
    center = base_address + 3
    geometry = base_address + 4
    return {
        card: {
            "base": _table(base),
            "config": _table(config),
            "playing_card": _integer(live_id),
            "debuff": _boolean(False),
            "T": _table(geometry),
        },
        base: {
            "value": _string(rank),
            "suit": _string(suit),
        },
        config: {"center": _table(center)},
        center: {"key": _string("c_base")},
        geometry: {
            "x": _number(1.0),
            "y": _number(2.0),
            "w": _number(1.4),
            "h": _number(1.9),
        },
    }


def test_live_memory_snapshot_is_whitelisted_and_destroys_deck_order():
    GAME = 100
    STATES = 101
    CURRENT_ROUND = 102
    ROUND_RESETS = 103
    BLIND = 104
    HAND = 110
    HAND_CONFIG = 111
    HAND_CARDS = 112
    JOKERS = 120
    JOKER_CONFIG = 121
    JOKER_CARDS = 122
    CONSUMABLES = 130
    CONSUMABLE_CONFIG = 131
    CONSUMABLE_CARDS = 132
    DECK = 140
    DECK_CONFIG = 141
    DECK_CARDS = 142

    tables = {
        GAME: {
            "dollars": _integer(9),
            "round": _integer(1),
            "chips": _integer(120),
            "stake": _integer(1),
            "selected_back_key": _string("b_red"),
            "current_round": _table(CURRENT_ROUND),
            "round_resets": _table(ROUND_RESETS),
            "blind": _table(BLIND),
            "blind_on_deck": _string("Small"),
            "facing_blind": _boolean(True),
            "won": _boolean(False),
            # This deliberately exists in source state and must never be emitted.
            "pseudorandom": _table(999),
        },
        STATES: {"SELECTING_HAND": _number(1)},
        CURRENT_ROUND: {
            "hands_left": _integer(4),
            "discards_left": _integer(4),
        },
        ROUND_RESETS: {"ante": _integer(1)},
        BLIND: {
            "chips": _integer(300),
            "name": _string("Small Blind"),
            "boss": _boolean(False),
        },
        HAND: {"config": _table(HAND_CONFIG), "cards": _table(HAND_CARDS)},
        HAND_CONFIG: {"card_limit": _integer(8)},
        JOKERS: {"config": _table(JOKER_CONFIG), "cards": _table(JOKER_CARDS)},
        JOKER_CONFIG: {"card_limit": _integer(5)},
        CONSUMABLES: {
            "config": _table(CONSUMABLE_CONFIG),
            "cards": _table(CONSUMABLE_CARDS),
        },
        CONSUMABLE_CONFIG: {"card_limit": _integer(2)},
        DECK: {"config": _table(DECK_CONFIG), "cards": _table(DECK_CARDS)},
        DECK_CONFIG: {"card_limit": _integer(52)},
    }

    tables.update(_card_tables(200, rank="A", suit="Hearts", live_id=10))
    tables.update(_card_tables(210, rank="K", suit="Spades", live_id=11))
    # Intentionally reverse public canonical ordering inside the live deck array.
    tables.update(_card_tables(220, rank="K", suit="Spades", live_id=20))
    tables.update(_card_tables(230, rank="A", suit="Hearts", live_id=21))

    arrays = {
        HAND_CARDS: [_table(200), _table(210)],
        JOKER_CARDS: [],
        CONSUMABLE_CARDS: [],
        DECK_CARDS: [_table(220), _table(230)],
    }
    decoder = _FakeDecoder(tables, arrays)
    root = {
        "GAME": _table(GAME),
        "STATE": _number(1),
        "STATE_COMPLETE": _boolean(True),
        "STATES": _table(STATES),
        "hand": _table(HAND),
        "jokers": _table(JOKERS),
        "consumeables": _table(CONSUMABLES),
        "deck": _table(DECK),
    }

    payload, phase, state_complete = snapshot_payload_from_live_memory(decoder, root)

    assert phase == "SELECTING_HAND"
    assert state_complete is True
    assert payload["deck"] == "RED"
    assert payload["stake"] == "WHITE"
    assert payload["money"] == 9
    assert payload["score"] == 120
    assert payload["round"]["chips"] == 300
    assert payload["hidden_rng_exposed"] is False
    assert payload["hidden_draw_order_exposed"] is False
    assert "pseudorandom" not in payload

    hand = payload["hand"]["cards"]
    assert [card["live_id"] for card in hand] == [10, 11]
    assert [card["value"]["rank"] for card in hand] == ["A", "K"]

    remaining = payload["cards"]["cards"]
    assert [card["value"]["rank"] for card in remaining] == ["A", "K"]
    assert [card["live_id"] for card in remaining] == [21, 20]


def test_live_memory_observer_whitelists_dynamic_joker_targets_and_hand_counts():
    CURRENT_ROUND = 300
    CASTLE_CARD = 301
    IDOL_CARD = 302
    HANDS = 310
    PAIR = 311

    tables = {
        CURRENT_ROUND: {
            "castle_card": _table(CASTLE_CARD),
            "idol_card": _table(IDOL_CARD),
            # Unrelated round state must not leak through the helper.
            "reroll_cost": _integer(99),
        },
        CASTLE_CARD: {
            "suit": _string("Clubs"),
            "secret": _string("do-not-expose"),
        },
        IDOL_CARD: {
            "rank": _string("Ace"),
            "suit": _string("Spades"),
            "id": _integer(14),
        },
        HANDS: {"Pair": _table(PAIR)},
        PAIR: {
            "level": _integer(3),
            "played": _integer(7),
            "played_this_round": _integer(2),
        },
    }
    decoder = _FakeDecoder(tables, {})

    round_state = _normalize_round_joker_public_state(
        decoder,
        decoder.string_fields(CURRENT_ROUND),
    )
    hands = _normalize_hand_levels(decoder, _table(HANDS))

    assert round_state == {
        "j_castle": {"suit": "Clubs"},
        "j_idol": {"rank": "Ace", "suit": "Spades"},
    }
    assert hands == {"Pair": {"level": 3, "played": 7}}
