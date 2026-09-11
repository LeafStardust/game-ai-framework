from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.live.held_planet_parity_capture import (
    LiveConsumableUsageState,
    LiveHeldPlanetParityCaptureError,
    LiveHeldPlanetParityCheckpoint,
    LiveHeldPlanetParityRecorder,
    capture_live_held_planet_parity_checkpoint,
    compare_captured_live_held_planet,
    headless_held_planet_run_from_checkpoint,
    held_planet_parity_checkpoint_from_payload,
    held_planet_parity_checkpoint_to_payload,
)
from games.balatro.live.injected.hand_dispatcher import LiveInjectedActionResult
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.luajit_memory import LuaValue


def _planet():
    return {
        "ability_name": "Pluto",
        "ability_set": "Planet",
        "area_index": 2,
        "cost": 3,
        "label": "Pluto",
        "live_id": 41,
    }


def _snapshot(sequence, *, planet=True, level=1, phase="SHOP", constellation=1.0):
    consumables = [_planet()] if planet else []
    jokers = []
    if constellation is not None:
        jokers.append(
            {
                "ability_name": "Constellation",
                "ability_set": "Joker",
                "center": "j_constellation",
                "label": "Constellation",
                "rarity": "UNCOMMON",
                "public_state": {"x_mult": constellation},
            }
        )
    return LiveBalatroSnapshot(
        sequence,
        phase,
        True,
        {
            "deck": "RED",
            "stake": "WHITE",
            "money": 10,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 0},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "count": len(jokers), "cards": jokers},
            "consumables": {
                "limit": 2,
                "count": len(consumables),
                "cards": consumables,
            },
            "hands": {"High Card": {"level": level}},
            "last_tarot_planet": "c_pluto" if level > 1 else None,
        },
    )


def _usage(*, pluto=0):
    counts = {"c_pluto": pluto} if pluto else {}
    sets = {"c_pluto": "Planet"} if pluto else {}
    return LiveConsumableUsageState(
        counts=counts,
        sets=sets,
        totals={
            "tarot": 0,
            "planet": pluto,
            "spectral": 0,
            "tarot_planet": pluto,
            "all": pluto,
        },
    )


def _checkpoint(*, pluto=0):
    return LiveHeldPlanetParityCheckpoint(_snapshot(1), _usage(pluto=pluto))


def _action(*, name="Pluto", area_index=2, cards=()):
    return BalatroAction(
        USE_CONSUMABLE,
        cards=list(cards),
        target=SimpleNamespace(area_index=area_index, name=name, label=name),
    )


def test_env_r5_private_held_planet_checkpoint_replays_exact_public_and_usage_state():
    comparison = compare_captured_live_held_planet(
        _checkpoint(pluto=2),
        _action(),
        _snapshot(2, planet=False, level=2, constellation=1.1),
        _usage(pluto=3),
    )

    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_private_held_planet_checkpoint_restores_complete_usage_authority():
    run = headless_held_planet_run_from_checkpoint(_checkpoint(pluto=2))

    assert run.consumable_usage_observed is True
    assert run.consumable_usage_counts == {"c_pluto": 2}
    assert run.consumable_usage_totals == {
        "tarot": 0,
        "planet": 2,
        "spectral": 0,
        "tarot_planet": 2,
        "all": 2,
    }


@pytest.mark.parametrize(
    ("after", "after_usage", "difference"),
    [
        (_snapshot(2, planet=False, level=3, constellation=1.1), _usage(pluto=3), "public.after"),
        (_snapshot(2, planet=False, level=2, constellation=1.1), _usage(pluto=4), "private.usage_counts"),
        (
            _snapshot(2, planet=False, level=2, constellation=1.1),
            LiveConsumableUsageState(
                counts={"c_pluto": 3},
                sets={"c_pluto": "Tarot"},
                totals=_usage(pluto=3).totals,
            ),
            "private.usage_sets",
        ),
    ],
)
def test_env_r5_private_held_planet_comparison_reports_exact_difference(
    after,
    after_usage,
    difference,
):
    comparison = compare_captured_live_held_planet(
        _checkpoint(pluto=2),
        _action(),
        after,
        after_usage,
    )

    assert comparison.matches is False
    assert difference in comparison.differences


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (_action(name="Mercury"), "name does not match"),
        (_action(area_index=True), "nonnegative integer"),
        (_action(cards=(object(),)), "must not target hand cards"),
        (BalatroAction("BUY_JOKER"), "accepts only USE_CONSUMABLE"),
    ],
)
def test_env_r5_private_held_planet_action_fails_closed(action, message):
    with pytest.raises(LiveHeldPlanetParityCaptureError, match=message):
        compare_captured_live_held_planet(
            _checkpoint(),
            action,
            _snapshot(2, planet=False, level=2, constellation=1.1),
            _usage(pluto=1),
        )


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, *, pluto=0, malformed=None):
        usage = {}
        if pluto:
            usage["c_pluto"] = _lua("table", 300)
        totals = {
            "tarot": _lua("number", 0.0),
            "planet": _lua("number", float(pluto)),
            "spectral": _lua("number", 0.0),
            "tarot_planet": _lua("number", float(pluto)),
            "all": _lua("number", float(pluto)),
        }
        self.tables = {
            100: {
                "consumeable_usage": _lua("table", 200),
                "consumeable_usage_total": _lua("table", 400),
            },
            200: usage,
            300: {
                "count": _lua("number", float(pluto)),
                "order": _lua("number", 1.0),
                "set": _lua("string", "Planet"),
            },
            400: totals,
        }
        if malformed == "unknown_center":
            self.tables[200]["c_not_real"] = _lua("table", 300)
        elif malformed == "wrong_set":
            self.tables[300]["set"] = _lua("string", "Tarot")
        elif malformed == "incomplete_totals":
            del self.tables[400]["spectral"]
        elif malformed == "inconsistent_totals":
            self.tables[400]["all"] = _lua("number", float(pluto + 1))

    def string_fields(self, address):
        return dict(self.tables[address])


class _Observer:
    def __init__(self, *, pluto=0, malformed=None):
        self.snapshot = _snapshot(1)
        self.decoder = _Decoder(pluto=pluto, malformed=malformed)

    def observe(self):
        return deepcopy(self.snapshot)

    def _root(self):
        return self.decoder, 0, {"GAME": _lua("table", 100)}


class _SettlingObserver(_Observer):
    def __init__(self):
        super().__init__(pluto=1)
        self.root_reads = 0

    def _root(self):
        self.root_reads += 1
        if self.root_reads == 2:
            self.decoder = _Decoder(pluto=2)
        return super()._root()


class _DriftingObserver(_Observer):
    def __init__(self):
        super().__init__(pluto=1)
        self.root_reads = 0

    def _root(self):
        self.root_reads += 1
        self.decoder = _Decoder(pluto=1 if self.root_reads % 2 else 2)
        return super()._root()


def _set_observer_usage(observer, pluto):
    observer.decoder = _Decoder(pluto=pluto)


def test_env_r5_held_planet_capture_reads_stable_private_usage_authority():
    checkpoint = capture_live_held_planet_parity_checkpoint(_Observer(pluto=2))

    assert checkpoint.usage == _usage(pluto=2)


def test_env_r5_held_planet_capture_normalizes_vanilla_nil_history_to_exact_zero():
    observer = _Observer()
    observer.decoder.tables[100] = {}

    checkpoint = capture_live_held_planet_parity_checkpoint(observer)

    assert checkpoint.usage == _usage()


def test_env_r5_held_planet_capture_normalizes_vanilla_empty_usage_before_lazy_totals():
    observer = _Observer()
    del observer.decoder.tables[100]["consumeable_usage_total"]

    checkpoint = capture_live_held_planet_parity_checkpoint(observer)

    assert checkpoint.usage == _usage()


def test_env_r5_held_planet_capture_rejects_nonempty_usage_without_totals():
    observer = _Observer(pluto=1)
    del observer.decoder.tables[100]["consumeable_usage_total"]

    with pytest.raises(
        LiveHeldPlanetParityCaptureError,
        match="only partially available",
    ):
        capture_live_held_planet_parity_checkpoint(observer)


def test_env_r5_held_planet_capture_waits_for_private_usage_to_settle():
    checkpoint = capture_live_held_planet_parity_checkpoint(
        _SettlingObserver(),
        stability_interval_seconds=0,
    )

    assert checkpoint.usage == _usage(pluto=2)


def test_env_r5_held_planet_capture_rejects_continuous_private_usage_drift():
    with pytest.raises(LiveHeldPlanetParityCaptureError, match="bounded"):
        capture_live_held_planet_parity_checkpoint(
            _DriftingObserver(),
            stability_attempts=4,
            stability_interval_seconds=0,
        )


def test_env_r5_held_planet_capture_requires_complete_shop():
    observer = _Observer()
    observer.snapshot = _snapshot(1, phase="SELECTING_HAND")

    with pytest.raises(LiveHeldPlanetParityCaptureError, match="complete SHOP"):
        capture_live_held_planet_parity_checkpoint(observer)


@pytest.mark.parametrize(
    ("malformed", "message"),
    [
        ("unknown_center", "unknown center"),
        ("wrong_set", "set is inconsistent"),
        ("incomplete_totals", "incomplete"),
        ("inconsistent_totals", "counts and totals are inconsistent"),
    ],
)
def test_env_r5_held_planet_capture_rejects_malformed_private_authority(
    malformed,
    message,
):
    with pytest.raises(LiveHeldPlanetParityCaptureError, match=message):
        capture_live_held_planet_parity_checkpoint(
            _Observer(pluto=1, malformed=malformed)
        )


def test_env_r5_held_planet_checkpoint_payload_roundtrip():
    checkpoint = _checkpoint(pluto=2)
    assert held_planet_parity_checkpoint_from_payload(
        held_planet_parity_checkpoint_to_payload(checkpoint)
    ) == checkpoint


def test_env_r5_held_planet_recorder_preserves_private_before_and_after(tmp_path):
    observer = _Observer(pluto=2)
    action = _action()
    decision = SimpleNamespace(snapshot=observer.snapshot, action=action)
    recorder = LiveHeldPlanetParityRecorder("attempt-001", observer, directory=tmp_path)
    before = recorder.capture_before(decision)
    after = _snapshot(2, planet=False, level=2, constellation=1.1)
    observer.snapshot = after
    _set_observer_usage(observer, 3)
    dispatch = LiveInjectedActionResult(action, decision.snapshot, after)

    comparison = recorder.record_after(before, decision, dispatch)

    assert comparison.matches is True
    row = json.loads(recorder.path.read_text(encoding="utf-8"))
    assert row["schema"] == "balatro-r5-held-planet-parity-v1"
    assert row["before"]["usage"]["counts"] == {"c_pluto": 2}
    assert row["after_usage"]["counts"] == {"c_pluto": 3}


def test_env_r5_supervisor_held_planet_capture_is_observational_only(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    before = _snapshot(1)
    after = _snapshot(2, planet=False, level=2, constellation=1.1)
    action = _action()
    decision = SimpleNamespace(snapshot=before, action=action)
    dispatch = LiveInjectedActionResult(action, before, after)
    execution = (dispatch, {"achievement": "unchanged"})

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            self.executions = 0

        def decide(self):
            raise AssertionError("not used")

        def execute(self, received):
            assert received is decision
            self.executions += 1
            return execution

    class FakeControl:
        def read_status(self):
            return {"run_id": "attempt-001", "state": "RUNNING"}

    class FakeRecorder:
        instances = []

        def __init__(self, run_id, observer, *, directory):
            self.run_id = run_id
            self.path = tmp_path / "private.jsonl"
            self.__class__.instances.append(self)

        def capture_before(self, received):
            assert received is decision
            return "private-before"

        def record_after(self, pending, received, result):
            assert pending == "private-before"
            assert received is decision
            assert result is dispatch
            return SimpleNamespace(
                matches=False,
                differences=("private.usage_totals",),
            )

    monkeypatch.setattr(
        entry,
        "StrategyAwareLiveMemoryInjectedSingleStepRunner",
        FakeRunner,
    )
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveHeldPlanetParityRecorder", FakeRecorder)
    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        held_planet_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    assert FakeRecorder.instances[0].run_id == "attempt-001"
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "held_planet_parity_mismatch"
    assert diagnostic["data"]["differences"] == ["private.usage_totals"]
