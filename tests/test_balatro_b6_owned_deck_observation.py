from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.card import BalatroCard
from games.balatro.live.external.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


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
    return {
        card: {
            "base": _table(base),
            "config": _table(config),
            "playing_card": _integer(live_id),
            "debuff": _boolean(False),
        },
        base: {
            "value": _string(rank),
            "suit": _string(suit),
        },
        config: {"center": _table(center)},
        center: {"key": _string("c_base")},
    }


def test_live_memory_snapshot_exposes_owned_deck_without_internal_order():
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
    PLAYING_CARDS = 150

    tables = {
        GAME: {
            "dollars": _integer(5),
            "round": _integer(1),
            "chips": _integer(0),
            "stake": _integer(1),
            "selected_back_key": _string("b_red"),
            "current_round": _table(CURRENT_ROUND),
            "round_resets": _table(ROUND_RESETS),
            "blind": _table(BLIND),
            "blind_on_deck": _string("Small"),
            "facing_blind": _boolean(True),
        },
        STATES: {"SELECTING_HAND": _number(1)},
        CURRENT_ROUND: {
            "hands_left": _integer(4),
            "discards_left": _integer(3),
        },
        ROUND_RESETS: {"ante": _integer(1)},
        BLIND: {"chips": _integer(300), "boss": _boolean(False)},
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

    tables.update(_card_tables(200, rank="2", suit="Hearts", live_id=10))
    tables.update(_card_tables(210, rank="A", suit="Hearts", live_id=20))
    tables.update(_card_tables(220, rank="K", suit="Spades", live_id=21))
    tables.update(_card_tables(230, rank="3", suit="Clubs", live_id=22))

    arrays = {
        HAND_CARDS: [_table(200)],
        JOKER_CARDS: [],
        CONSUMABLE_CARDS: [],
        DECK_CARDS: [_table(220)],
        # Deliberately non-canonical internal creation order.
        PLAYING_CARDS: [_table(220), _table(210), _table(230)],
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
        "playing_cards": _table(PLAYING_CARDS),
    }

    payload, phase, complete = snapshot_payload_from_live_memory(decoder, root)

    assert phase == "SELECTING_HAND"
    assert complete is True
    assert [card["live_id"] for card in payload["cards"]["cards"]] == [21]
    owned = payload["owned_cards"]["cards"]
    assert [card["value"]["rank"] for card in owned] == ["3", "A", "K"]
    assert [card["live_id"] for card in owned] == [22, 20, 21]
    assert payload["hidden_draw_order_exposed"] is False


def test_translator_keeps_remaining_and_owned_decks_separate():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "cards": {
                "count": 1,
                "limit": 52,
                "cards": [
                    {"value": {"rank": "K", "suit": "S"}, "live_id": 21}
                ],
            },
            "owned_cards": {
                "count": 2,
                "limit": 2,
                "cards": [
                    {"value": {"rank": "A", "suit": "H"}, "live_id": 20},
                    {"value": {"rank": "K", "suit": "S"}, "live_id": 21},
                ],
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert [(card.rank, card.suit) for card in state.deck] == [("K", "Spades")]
    assert state.owned_deck is not None
    assert [(card.rank, card.suit) for card in state.owned_deck] == [
        ("A", "Hearts"),
        ("K", "Spades"),
    ]


def test_translator_preserves_unknown_owned_deck_when_payload_omits_it():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"cards": {"count": 0, "limit": 52, "cards": []}},
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.owned_deck is None


def test_build_profiler_prefers_owned_deck_but_falls_back_for_old_states():
    state = BalatroState()
    state.deck = [BalatroCard("2", "Hearts")]
    state.owned_deck = [
        BalatroCard("K", "Spades"),
        BalatroCard("K", "Clubs"),
    ]

    profile = BalatroBuildProfiler().profile(state)

    assert profile.deck_size == 2
    assert dict(profile.rank_counts) == {"K": 2}
    assert dict(profile.suit_counts) == {"Clubs": 1, "Spades": 1}

    state.owned_deck = None
    fallback = BalatroBuildProfiler().profile(state)
    assert fallback.deck_size == 1
    assert dict(fallback.rank_counts) == {"2": 1}


def test_state_copy_preserves_owned_deck_contract():
    state = BalatroState()
    state.owned_deck = [BalatroCard("A", "Spades")]

    copied = state.copy()

    assert copied.owned_deck is not None
    assert copied.owned_deck is not state.owned_deck
    assert copied.owned_deck[0] is state.owned_deck[0]

    state.owned_deck = None
    assert state.copy().owned_deck is None
