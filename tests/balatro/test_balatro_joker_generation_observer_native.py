import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.joker_generation_pool_live_state_policy import (
    install_joker_generation_pool_live_state_policy,
)
from games.balatro.live import joker_generation_pool_state
from games.balatro.live.joker_generation_pool_state import (
    JokerGenerationPoolLiveMemoryObserver,
)
from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)


def test_supervisor_composes_native_joker_generation_observer():
    assert issubclass(
        JokerGenerationPoolLiveMemoryObserver,
        live_memory_observer.LiveMemoryBalatroObserver,
    )
    assert issubclass(
        SupervisorLiveMemoryBalatroObserver,
        JokerGenerationPoolLiveMemoryObserver,
    )


def test_enriched_public_generation_state_participates_in_sequence(monkeypatch):
    observer = JokerGenerationPoolLiveMemoryObserver(
        decoder=object(),
        g_table=1,
    )
    monkeypatch.setattr(observer, "_root", lambda: (object(), 1, {}))
    monkeypatch.setattr(
        live_memory_observer,
        "snapshot_payload_from_live_memory",
        lambda _decoder, _root: ({"money": 4}, "SHOP", True),
    )

    generation_state = {"joker_generation_pool_observed": True}
    monkeypatch.setattr(
        joker_generation_pool_state,
        "observe_joker_generation_state",
        lambda _decoder, _root, _payload, _phase: dict(generation_state),
    )

    first = observer.observe()
    second = observer.observe()
    assert first.sequence == second.sequence
    assert first.payload["joker_generation_pool_observed"] is True

    generation_state["joker_generation_pool_observed"] = False
    third = observer.observe()
    assert third.sequence == second.sequence + 1
    assert third.payload["joker_generation_pool_observed"] is False


def test_retired_installer_does_not_mutate_base_observer():
    before = live_memory_observer.snapshot_payload_from_live_memory

    install_joker_generation_pool_live_state_policy()

    assert live_memory_observer.snapshot_payload_from_live_memory is before
    assert not hasattr(
        live_memory_observer,
        "_joker_generation_pool_snapshot_installed",
    )
