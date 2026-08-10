from games.balatro.live import (
    DefaultBalatroStateTranslator,
    LiveBalatroSnapshot,
)


def test_translator_maps_live_scalar_state():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="ROUND_START",
        state_complete=True,
        payload={
            "money": 14,
            "ante": 3,
            "round": 2,
            "blind_score": 900,
            "discards_left": 4,
            "hand_size": 8,
            "consumable_slots": 2,
            "stake": 1,
            "deck_name": "Red Deck",
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.money == 14
    assert state.ante == 3
    assert state.round == 2
    assert state.blind_score == 900
    assert state.discards_remaining == 4
    assert state.hand_size == 8
    assert state.stake_name == "WHITE"
    assert state.phase == "ROUND_START"


def test_translator_maps_live_cards_and_modifiers():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="ROUND_START",
        state_complete=True,
        payload={
            "hand": [
                {
                    "rank": "Ace",
                    "suit": "Spades",
                    "enhancement": "m_steel",
                    "edition": "foil",
                    "seal": "Red",
                }
            ],
            "deck": [
                {
                    "rank": "King",
                    "suit": "Hearts",
                }
            ],
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.hand) == 1
    assert state.hand[0].rank == "A"
    assert state.hand[0].suit == "Spades"
    assert state.hand[0].enhancement == "Steel"
    assert state.hand[0].edition == "Foil"
    assert state.hand[0].seal == "Red"
    assert len(state.deck) == 1
    assert state.deck[0].rank == "K"


def test_translator_maps_blind_requirement():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="ROUND_START",
        state_complete=True,
        payload={
            "blind": {
                "name": "The Wall",
                "chips": 5000,
                "boss": True,
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.blind is not None
    assert state.blind.requirement == 5000
    assert state.boss_name == "The Wall"
