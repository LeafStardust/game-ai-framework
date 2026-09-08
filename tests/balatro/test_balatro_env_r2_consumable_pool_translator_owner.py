import games.balatro.live.translator as translator_module
from games.balatro.live.protocol import LiveBalatroSnapshot


def test_env_r2_default_translator_invokes_strict_consumable_pool_owner(monkeypatch):
    calls = []
    original = translator_module.translate_consumable_generation_pool_payload

    def spy(state, payload):
        original(state, payload)
        calls.append(
            (
                state.consumable_generation_pool_observed,
                state.consumable_generation_pools.copy(),
            )
        )

    monkeypatch.setattr(
        translator_module,
        "translate_consumable_generation_pool_payload",
        spy,
    )
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "consumable_generation_pool_observed": True,
            "consumable_generation_pools": {
                "Tarot": [
                    {
                        "type": "Tarot",
                        "key": "c_strength",
                        "cost": 3,
                        "unlocked": True,
                        "no_pool_flag": None,
                        "yes_pool_flag": None,
                        "softlock": False,
                        "hand_type": None,
                    }
                ],
                "Planet": [
                    {
                        "type": "Planet",
                        "key": "c_pluto",
                        "cost": 3,
                        "unlocked": True,
                        "no_pool_flag": None,
                        "yes_pool_flag": None,
                        "softlock": False,
                        "hand_type": None,
                    }
                ],
            },
        },
    )

    state = translator_module.DefaultBalatroStateTranslator().translate(snapshot)

    assert len(calls) == 1
    assert calls[0][0] is True
    assert set(calls[0][1]) == {"Tarot", "Planet"}
    assert state.consumable_generation_pool_observed is True
    assert set(state.consumable_generation_pools) == {"Tarot", "Planet"}
