from games.balatro.actions import BalatroAction, USE_CONSUMABLE
from games.balatro.live import (
    DefaultBalatroActionExecutor,
    DefaultBalatroStateTranslator,
    LiveBalatroSnapshot,
)


def test_translator_creates_live_tarot_inventory_item():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "consumables": [
                {
                    "id": "consumable-1",
                    "ability_name": "Strength",
                }
            ]
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert len(state.consumables) == 1
    assert state.consumables[0].name == "Strength"
    assert state.consumables[0].live_id == "consumable-1"


def test_use_consumable_command_maps_consumable_and_card_ids():
    snapshot = LiveBalatroSnapshot(
        sequence=8,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": [
                {
                    "id": "card-1",
                    "rank": "2",
                    "suit": "Hearts",
                }
            ],
            "consumables": [
                {
                    "id": "consumable-1",
                    "ability_name": "Strength",
                }
            ],
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
        "cards": ["card-1"],
        "target": "consumable-1",
    }
