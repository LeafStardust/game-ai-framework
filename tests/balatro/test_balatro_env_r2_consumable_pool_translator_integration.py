from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _record(card_type: str, key: str):
    return {
        "type": card_type,
        "key": key,
        "cost": 3,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }


def test_env_r2_default_translator_installs_consumable_generation_catalogue():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "deck_name": "RED",
            "stake_name": "WHITE",
            "consumable_generation_pool_observed": True,
            "consumable_generation_pools": {
                "Tarot": [_record("Tarot", "c_strength")],
                "Planet": [_record("Planet", "c_pluto")],
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.consumable_generation_pool_observed is True
    assert state.consumable_generation_pools["Tarot"][0]["key"] == "c_strength"
    assert state.consumable_generation_pools["Planet"][0]["key"] == "c_pluto"


def test_env_r2_default_translator_fails_closed_on_partial_consumable_catalogue():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "deck_name": "RED",
            "stake_name": "WHITE",
            "consumable_generation_pool_observed": True,
            "consumable_generation_pools": {
                "Tarot": [_record("Tarot", "c_strength")],
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.consumable_generation_pool_observed is False
    assert state.consumable_generation_pools == {}
