from games.balatro.actions import BalatroAction, USE_CONSUMABLE
from games.balatro.live import (
    DefaultBalatroActionExecutor,
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


def test_use_consumable_command_maps_balatrobot_indices():
    snapshot = LiveBalatroSnapshot(
        sequence=8,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {
                "count": 1,
                "limit": 8,
                "cards": [
                    {
                        "value": {
                            "rank": "2",
                            "suit": "H",
                        },
                        "modifier": {},
                    }
                ],
            },
            "consumables": {
                "count": 1,
                "limit": 2,
                "cards": [
                    {
                        "key": "c_strength",
                        "set": "TAROT",
                        "label": "Strength",
                    }
                ],
            },
        },
    )
    state = DefaultBalatroStateTranslator().translate(snapshot)

    command = DefaultBalatroActionExecutor().command_for(
        BalatroAction(
            USE_CONSUMABLE,
            cards=[state.hand[0]],
            target=state.consumables[0],
        ),
        snapshot,
    )

    assert command.action == USE_CONSUMABLE
    assert command.payload == {
        "cards": [0],
        "target": 0,
    }
