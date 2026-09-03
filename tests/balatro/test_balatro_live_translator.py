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
                        "debuff": True,
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
    assert state.hand[0].debuffed is True
    assert len(state.deck) == 1
    assert state.deck[0].rank == "K"
    assert state.deck[0].suit == "Hearts"
    assert state.deck[0].debuffed is False


def test_translator_maps_current_blind_requirement_and_reward():
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
                    "reward": 3,
                },
                "big": {
                    "type": "BIG",
                    "status": "DEFEATED",
                    "name": "Big Blind",
                    "score": 450,
                    "reward": 4,
                },
                "boss": {
                    "type": "BOSS",
                    "status": "CURRENT",
                    "name": "The Wall",
                    "score": 5000,
                    "reward": 5,
                },
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.blind is not None
    assert state.blind.requirement == 5000
    assert state.blind.reward == 5
    assert state.boss_name == "The Wall"


def test_translator_maps_live_poker_hand_levels_and_play_counts():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "hands": {
                "Pair": {"level": 3, "played": 7},
                "Flush": {"level": 2, "played": 4},
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.hand_levels["PAIR"] == 3
    assert state.hand_levels["FLUSH"] == 2
    assert state.hand_play_counts["PAIR"] == 7
    assert state.hand_play_counts["FLUSH"] == 4


def test_translator_clears_previous_round_hand_counts_outside_active_round():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "hands": {
                "Pair": {"level": 3, "played": 7, "played_this_round": 2},
                "Flush": {"level": 2, "played": 4, "played_this_round": 1},
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.round_hand_play_counts["PAIR"] == 0
    assert state.round_hand_play_counts["FLUSH"] == 0


def test_translator_preserves_current_round_hand_counts_while_selecting_hand():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hands": {
                "Pair": {"level": 3, "played": 7, "played_this_round": 2},
                "Flush": {"level": 2, "played": 4, "played_this_round": 1},
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.round_hand_play_counts["PAIR"] == 2
    assert state.round_hand_play_counts["FLUSH"] == 1
