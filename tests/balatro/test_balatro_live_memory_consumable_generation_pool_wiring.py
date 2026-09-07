from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime import live_memory_discard_history_observer as subject
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    DiscardHistorySupervisorLiveMemoryBalatroObserver,
    enrich_consumable_generation_pool_payload,
)
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)


def _pool():
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


def test_production_live_observer_installs_authoritative_consumable_generation_pool(
    monkeypatch,
):
    base = LiveBalatroSnapshot(
        sequence=17,
        phase="SHOP",
        state_complete=True,
        payload={},
    )
    generation_pool = _pool()

    monkeypatch.setattr(
        SupervisorLiveMemoryBalatroObserver,
        "_observe_public",
        lambda self: base,
    )
    monkeypatch.setattr(
        DiscardHistorySupervisorLiveMemoryBalatroObserver,
        "_root",
        lambda self: (object(), None, {}),
    )
    monkeypatch.setattr(subject, "public_discard_history", lambda decoder, root: None)
    monkeypatch.setattr(
        subject, "public_forced_selection_flags", lambda decoder, root: None
    )
    monkeypatch.setattr(subject, "public_joker_generation_pools", lambda decoder, root: {})
    monkeypatch.setattr(
        subject,
        "public_consumable_generation_pool",
        lambda decoder, root: generation_pool,
    )

    observer = DiscardHistorySupervisorLiveMemoryBalatroObserver.__new__(
        DiscardHistorySupervisorLiveMemoryBalatroObserver
    )
    snapshot = observer._observe_public()

    assert snapshot.payload["consumable_generation_pool_observed"] is True
    assert snapshot.payload["consumable_generation_pool"] == generation_pool


def test_consumable_generation_pool_enrichment_clears_stale_authority():
    payload = {
        "consumable_generation_pool_observed": True,
        "consumable_generation_pool": _pool(),
    }

    enriched = enrich_consumable_generation_pool_payload(payload, None)

    assert enriched["consumable_generation_pool_observed"] is False
    assert "consumable_generation_pool" not in enriched
    assert "consumable_generation_pool" in payload
