from games.balatro.live.runtime import consumable_generation_pool_snapshot as subject


def test_env_r2_consumable_pool_snapshot_emits_complete_observation(monkeypatch):
    observed = {
        "Tarot": [{"type": "Tarot", "key": "c_strength", "cost": 3}],
        "Planet": [{"type": "Planet", "key": "c_pluto", "cost": 3}],
    }
    monkeypatch.setattr(
        subject,
        "observe_consumable_generation_pools",
        lambda decoder, root: observed,
    )
    payload = {}

    subject.augment_consumable_generation_pool_payload(object(), {}, payload)

    assert payload["consumable_generation_pool_observed"] is True
    assert payload["consumable_generation_pools"] == observed
    assert payload["consumable_generation_pools"] is not observed
    payload["consumable_generation_pools"]["Tarot"][0]["cost"] = 9
    assert observed["Tarot"][0]["cost"] == 3


def test_env_r2_consumable_pool_snapshot_marks_failed_observation_and_removes_stale_data(monkeypatch):
    monkeypatch.setattr(
        subject,
        "observe_consumable_generation_pools",
        lambda decoder, root: None,
    )
    payload = {
        "consumable_generation_pool_observed": True,
        "consumable_generation_pools": {"Tarot": [], "Planet": []},
    }

    subject.augment_consumable_generation_pool_payload(object(), {}, payload)

    assert payload["consumable_generation_pool_observed"] is False
    assert "consumable_generation_pools" not in payload
