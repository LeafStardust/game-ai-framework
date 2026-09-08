from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


def test_translator_preserves_agent_facing_live_card_id():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {
                "limit": 8,
                "cards": [
                    {
                        "value": {"rank": "Ace", "suit": "Spades"},
                        "modifier": {},
                        "live_id": 31,
                    }
                ],
            },
            "cards": {"cards": []},
            "jokers": {"cards": []},
            "consumables": {"cards": []},
            "round": {"chips": 300, "hands_left": 4, "discards_left": 4},
            "blind": {"type": "SMALL", "score": 300, "status": "CURRENT"},
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.hand) == 1
    assert state.hand[0].rank == "A"
    assert state.hand[0].suit == "Spades"
    assert state.hand[0].live_id == 31
