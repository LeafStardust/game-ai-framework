import pytest

from games.balatro.live.consumable_generation_pool_translation import (
    translate_consumable_generation_pool_payload,
)
from games.balatro.state import BalatroState


def _record(card_type: str, key: str, **extra):
    record = {
        "type": card_type,
        "key": key,
        "cost": 3,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }
    record.update(extra)
    return record


def _payload():
    return {
        "consumable_generation_pool_observed": True,
        "consumable_generation_pools": {
            "Tarot": [_record("Tarot", "c_strength")],
            "Planet": [_record("Planet", "c_pluto")],
        },
    }


def test_env_r2_consumable_pool_translation_installs_complete_catalogue():
    state = BalatroState()
    payload = _payload()

    translate_consumable_generation_pool_payload(state, payload)

    assert state.consumable_generation_pool_observed is True
    assert state.consumable_generation_pools == payload["consumable_generation_pools"]
    assert state.consumable_generation_pools is not payload["consumable_generation_pools"]


def test_env_r2_consumable_pool_translation_keeps_unobserved_source_unobserved():
    state = BalatroState()
    payload = _payload()
    payload["consumable_generation_pool_observed"] = False

    translate_consumable_generation_pool_payload(state, payload)

    assert state.consumable_generation_pool_observed is False
    assert state.consumable_generation_pools == {}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["consumable_generation_pools"].pop("Planet"),
        lambda payload: payload["consumable_generation_pools"].update(Spectral=[]),
        lambda payload: payload["consumable_generation_pools"]["Planet"].append("bad"),
        lambda payload: payload["consumable_generation_pools"]["Planet"][0].update(type="Tarot"),
        lambda payload: payload["consumable_generation_pools"]["Planet"][0].update(cost=True),
        lambda payload: payload["consumable_generation_pools"]["Planet"][0].update(extra="guess"),
        lambda payload: payload["consumable_generation_pools"]["Planet"].append(
            _record("Planet", "c_strength")
        ),
        lambda payload: payload["consumable_generation_pools"]["Planet"][0].update(
            softlock=True, hand_type=None
        ),
    ],
)
def test_env_r2_consumable_pool_translation_rejects_partial_or_malformed_catalogue(mutate):
    state = BalatroState()
    payload = _payload()
    mutate(payload)

    translate_consumable_generation_pool_payload(state, payload)

    assert state.consumable_generation_pool_observed is False
    assert state.consumable_generation_pools == {}


def test_env_r2_consumable_pool_translation_clears_prior_state_on_failed_refresh():
    state = BalatroState()
    translate_consumable_generation_pool_payload(state, _payload())
    assert state.consumable_generation_pool_observed is True

    bad = _payload()
    bad["consumable_generation_pools"]["Planet"][0]["cost"] = "3"
    translate_consumable_generation_pool_payload(state, bad)

    assert state.consumable_generation_pool_observed is False
    assert state.consumable_generation_pools == {}
