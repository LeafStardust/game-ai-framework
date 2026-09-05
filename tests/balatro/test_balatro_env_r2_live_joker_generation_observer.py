from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    enrich_joker_generation_pool_payload,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator


_POOLS = {
    1: [
        {
            "rarity": 1,
            "key": "j_joker",
            "unlocked": True,
            "no_pool_flag": None,
            "yes_pool_flag": None,
        },
        {
            "rarity": 1,
            "key": "j_greedy_joker",
            "unlocked": True,
            "no_pool_flag": None,
            "yes_pool_flag": None,
        },
    ],
    2: [],
    3: [],
    4: [],
}


def _translate(payload):
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload=payload,
    )
    return DefaultBalatroStateTranslator().translate(snapshot)


def test_env_r2_live_joker_pool_enrichment_round_trips_into_canonical_state():
    payload = enrich_joker_generation_pool_payload(
        {"money": 10, "joker_generation_pools": {1: [{"key": "stale"}]}},
        _POOLS,
    )

    assert payload["joker_generation_pool_observed"] is True
    assert payload["joker_generation_pools"] == _POOLS

    state = _translate(payload)
    assert state.joker_generation_pool_observed is True
    assert state.joker_generation_pools == _POOLS


def test_env_r2_live_joker_pool_incomplete_observation_clears_stale_catalogue():
    payload = enrich_joker_generation_pool_payload(
        {
            "money": 10,
            "joker_generation_pool_observed": True,
            "joker_generation_pools": _POOLS,
        },
        None,
    )

    assert payload["joker_generation_pool_observed"] is False
    assert "joker_generation_pools" not in payload

    state = _translate(payload)
    assert state.joker_generation_pool_observed is False
    assert state.joker_generation_pools == {}


def test_env_r2_live_joker_pool_enrichment_does_not_mutate_base_payload():
    base = {
        "money": 10,
        "joker_generation_pool_observed": True,
        "joker_generation_pools": _POOLS,
    }

    enriched = enrich_joker_generation_pool_payload(base, None)

    assert enriched is not base
    assert base["joker_generation_pool_observed"] is True
    assert base["joker_generation_pools"] == _POOLS
