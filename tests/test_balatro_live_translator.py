from games.balatro.live import (
    DefaultBalatroStateTranslator,
    LiveBalatroSnapshot,
)


def test_translator_maps_balatrobot_scalar_state():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "money": 14,
            "ante_num": 3,
            "round_num": 2,
            "deck": "RED",
            "stake": "WHITE",
            "round": {
                "chips": 900,
                "hands_left": 3,
                "discards_left": 4,
            },
            "hand": {
                "count": 0,
                "limit": 8,
                "cards": [],
            },
            "consumables": {
                "count": 0,
                "limit": 2,
                "cards": [],
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.money == 14
    assert state.ante == 3
    assert state.round == 2
    assert state.blind_score == 900
    assert state.hands_remaining == 3
    assert state.discards_remaining == 4
    assert state.hand_size == 8
    assert state.deck_name == "RED"
    assert state.stake_name == "WHITE"
    assert state.phase == "SELECTING_HAND"


def test_translator_maps_balatrobot_cards_and_modifiers():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {
                "count": 1,
                "limit": 8,
                "cards": [
                    {
                        "value": {
                            "rank": "A",
                            "suit": "S",
                        },
                        "modifier": {
                            "enhancement": "STEEL",
                            "edition": "FOIL",
                            "seal": "RED",
                        },
                    }
                ],
            },
            "cards": {
                "count": 1,
                "limit": 52,
                "cards": [
                    {
                        "value": {
                            "rank": "K",
                            "suit": "H",
                        },
                        "modifier": {},
                    }
                ],
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.hand) == 1
    assert state.hand[0].rank == "A"
    assert state.hand[0].suit == "Spades"
    assert state.hand[0].enhancement == "Steel"
    assert state.hand[0].edition == "Foil"
    assert state.hand[0].seal == "Red"
    assert state.hand[0].live_id == 0
    assert len(state.deck) == 1
    assert state.deck[0].rank == "K"
    assert state.deck[0].suit == "Hearts"


def test_translator_maps_current_blind_requirement():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "blinds": {
                "small": {
                    "type": "SMALL",
                    "status": "DEFEATED",
                    "name": "Small Blind",
                    "score": 300,
                },
                "big": {
                    "type": "BIG",
                    "status": "DEFEATED",
                    "name": "Big Blind",
                    "score": 450,
                },
                "boss": {
                    "type": "BOSS",
                    "status": "CURRENT",
                    "name": "The Wall",
                    "score": 5000,
                },
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.blind is not None
    assert state.blind.requirement == 5000
    assert state.boss_name == "The Wall"


def test_translator_maps_live_poker_hand_levels():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "hands": {
                "Pair": {"level": 3},
                "Flush": {"level": 2},
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.hand_levels["PAIR"] == 3
    assert state.hand_levels["FLUSH"] == 2
