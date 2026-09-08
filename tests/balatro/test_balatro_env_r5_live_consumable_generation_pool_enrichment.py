from games.balatro.live.consumable_generation_pool_translation import (
    translate_consumable_generation_pool_payload,
)
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    enrich_consumable_generation_pool_payload,
)
from games.balatro.state import BalatroState


def _generation_pools():
    return {
        "Tarot": [
            {
                "type": "Tarot",
                "key": "c_fool",
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
                "key": "c_mercury",
                "cost": 3,
                "unlocked": True,
                "no_pool_flag": None,
                "yes_pool_flag": None,
                "softlock": False,
                "hand_type": None,
            }
        ],
    }


def test_env_r5_live_consumable_generation_pool_enrichment_reaches_translator():
    pools = _generation_pools()

    payload = enrich_consumable_generation_pool_payload({}, pools)

    assert payload["consumable_generation_pool_observed"] is True
    assert payload["consumable_generation_pools"] == pools
    assert "consumable_generation_pool" not in payload

    state = BalatroState()
    translate_consumable_generation_pool_payload(state, payload)

    assert state.consumable_generation_pool_observed is True
    assert state.consumable_generation_pools == pools


def test_env_r5_live_consumable_generation_pool_enrichment_clears_stale_catalogue():
    payload = enrich_consumable_generation_pool_payload(
        {
            "consumable_generation_pool_observed": True,
            "consumable_generation_pools": _generation_pools(),
        },
        None,
    )

    assert payload["consumable_generation_pool_observed"] is False
    assert "consumable_generation_pools" not in payload

    state = BalatroState()
    translate_consumable_generation_pool_payload(state, payload)

    assert state.consumable_generation_pool_observed is False
    assert state.consumable_generation_pools == {}
