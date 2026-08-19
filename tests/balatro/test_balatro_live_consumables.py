from games.balatro.live import (
    DefaultBalatroStateTranslator,
    LiveBalatroSnapshot,
)


def test_translator_creates_balatrobot_tarot_inventory_item():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "consumables": {
                "count": 1,
                "limit": 2,
                "cards": [
                    {
                        "key": "c_strength",
                        "set": "TAROT",
                        "label": "Strength",
                        "cost": {
                            "buy": 3,
                            "sell": 1,
                        },
                    }
                ],
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.consumables) == 1
    assert state.consumables[0].name == "Strength"
    assert state.consumables[0].live_id == 0


def test_translator_accepts_numeric_save_state_consumable_cost():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=False,
        payload={
            "consumables": {
                "count": 1,
                "limit": 2,
                "cards": [
                    {
                        "live_id": 91,
                        "center": "c_strength",
                        "label": "Strength",
                        "ability_name": "Strength",
                        "ability_set": "Tarot",
                        "cost": 3,
                    }
                ],
            }
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.consumables) == 1
    assert state.consumables[0].name == "Strength"
    assert state.consumables[0].price == 3
