from types import SimpleNamespace

import games.balatro.live.external.live_memory_supervisor_observer as supervisor_observer_module
from games.balatro.live.external.balatro_agent_supervisor import (
    BalatroAgentSupervisor,
    DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
)
from games.balatro.live.external.live_memory_supervisor_observer import (
    DEFAULT_FULL_STATE_QUIET_SECONDS,
    SupervisorLiveMemoryBalatroObserver,
    joker_visual_signature,
    native_blind_select_ready,
    native_shop_ready,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return dict(self.tables.get(address, {}))


def _value(kind, value):
    return SimpleNamespace(kind=kind, value=value)


def _shop_snapshot(sequence: int, *, joker_x: float) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={
            "jokers": {
                "count": 1,
                "limit": 5,
                "cards": [
                    {
                        "live_id": 99,
                        "center": "j_joker",
                        "label": "Joker",
                        "ui": {"x": joker_x, "y": 1.0, "w": 1.0, "h": 1.4},
                        "public_state": {"mult": sequence},
                    }
                ],
            }
        },
    )


def _snapshot(
    sequence: int,
    *,
    phase: str = "SELECTING_HAND",
    complete: bool = True,
) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=complete,
        payload={"same_semantic_state": True},
    )


class _Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += float(seconds)


def test_native_blind_select_readiness_requires_real_on_deck_and_pane():
    decoder = _Decoder(
        {
            1: {},
            2: {},
        }
    )
    root = {
        "GAME": _value("table", 1),
        "blind_select_opts": _value("table", 2),
    }
    assert native_blind_select_ready(decoder, root) is False

    decoder.tables[1] = {"blind_on_deck": _value("string", "Small")}
    assert native_blind_select_ready(decoder, root) is False

    decoder.tables[2] = {"small": _value("table", 3)}
    assert native_blind_select_ready(decoder, root) is True


def test_native_shop_readiness_requires_real_card_areas_not_offer_counts():
    # Area tables: 10/20/30. Each has a real cards table and positive configured
    # capacity; the cards tables themselves are intentionally empty to prove that
    # purchases reducing visible offer count to zero do not make the shop unready.
    decoder = _Decoder(
        {
            10: {"cards": _value("table", 11), "config": _value("table", 12)},
            11: {},
            12: {"card_limit": _value("number", 2)},
            20: {"cards": _value("table", 21), "config": _value("table", 22)},
            21: {},
            22: {"card_limit": _value("number", 1)},
            30: {"cards": _value("table", 31), "config": _value("table", 32)},
            31: {},
            32: {"card_limit": _value("number", 2)},
        }
    )
    root = {}
    assert native_shop_ready(decoder, root) is False

    root["shop_jokers"] = _value("table", 10)
    assert native_shop_ready(decoder, root) is False

    root["shop_vouchers"] = _value("table", 20)
    assert native_shop_ready(decoder, root) is False

    root["shop_booster"] = _value("table", 30)
    assert native_shop_ready(decoder, root) is True

    # A zero/absent configured capacity is the signature of the premature SHOP
    # snapshot that previously normalized to count=0, limit=0 and triggered an
    # early END_SHOP.
    decoder.tables[12] = {"card_limit": _value("number", 0)}
    assert native_shop_ready(decoder, root) is False


def test_joker_visual_signature_tracks_geometry_not_strategic_state():
    first = _shop_snapshot(1, joker_x=2.0)
    same_position_new_state = _shop_snapshot(2, joker_x=2.0)
    moved = _shop_snapshot(3, joker_x=3.0)

    assert joker_visual_signature(first) == joker_visual_signature(same_position_new_state)
    assert joker_visual_signature(first) != joker_visual_signature(moved)


def test_post_pack_shop_waits_until_joker_geometry_is_stable(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(supervisor_observer_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(supervisor_observer_module, "sleep", clock.sleep)

    observer = SupervisorLiveMemoryBalatroObserver(
        post_pack_settle_seconds=0.10,
        joker_visual_stable_seconds=0.10,
        post_pack_settle_timeout_seconds=1.0,
        shop_readiness_poll_seconds=0.05,
    )
    snapshots = iter(
        [
            _shop_snapshot(2, joker_x=1.0),
            _shop_snapshot(3, joker_x=2.0),
            _shop_snapshot(4, joker_x=2.0),
            _shop_snapshot(5, joker_x=2.0),
        ]
    )
    observer._observe_public = lambda: next(snapshots)

    settled = observer._wait_for_post_pack_visual_settle(
        _shop_snapshot(1, joker_x=0.0)
    )

    assert settled.sequence == 5
    assert joker_visual_signature(settled) == joker_visual_signature(
        _shop_snapshot(99, joker_x=2.0)
    )
    assert clock.now >= 0.20


def test_full_state_quiet_barrier_resets_on_every_sequence_advance(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(supervisor_observer_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(supervisor_observer_module, "sleep", clock.sleep)

    observer = SupervisorLiveMemoryBalatroObserver(
        full_state_quiet_seconds=0.10,
        full_state_quiet_timeout_seconds=1.0,
        full_state_quiet_poll_seconds=0.05,
    )
    snapshots = iter(
        [
            _snapshot(2),
            _snapshot(3),
            _snapshot(3),
            _snapshot(3),
            _snapshot(3),
        ]
    )
    observer._observe_public = lambda: next(snapshots)

    settled = observer._wait_for_full_state_quiet(_snapshot(1))

    assert settled.sequence == 3
    # Sequence 1 was not allowed to count toward the final quiet period; both
    # later advances reset the clock before sequence 3 could be certified.
    assert clock.now >= 0.20
    assert observer._last_quiescent_sequence == 3


def test_full_state_quiet_barrier_reuses_already_certified_sequence():
    observer = SupervisorLiveMemoryBalatroObserver(
        full_state_quiet_seconds=0.10,
    )
    observer._last_quiescent_sequence = 7
    observer._observe_public = lambda: (_ for _ in ()).throw(
        AssertionError("already-certified sequence must not be polled again")
    )

    snapshot = _snapshot(7)
    assert observer._wait_for_full_state_quiet(snapshot) is snapshot


def test_default_full_state_quiet_window_is_one_second():
    assert DEFAULT_FULL_STATE_QUIET_SECONDS == 1.0


def test_supervisor_defaults_to_readiness_aware_observer_and_longer_bridge_timeout(tmp_path):
    supervisor = BalatroAgentSupervisor(
        session_directory=tmp_path / "sessions",
        run_log_directory=tmp_path / "runs",
    )

    assert supervisor.observer_factory is SupervisorLiveMemoryBalatroObserver

    runner = supervisor.runner_factory(SimpleNamespace())
    assert runner.bridge.timeout == DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS
    assert runner.bridge.timeout == 10.0
