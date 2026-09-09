from copy import deepcopy
from types import SimpleNamespace

import pytest

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.env.consumable_use import can_use_planet_exact
from games.balatro.env.strategic_evidence import use_planet_with_public_evidence
from games.balatro.live.held_planet_parity_capture import (
    LiveConsumableUsageState,
    LiveHeldPlanetParityCaptureError,
    LiveHeldPlanetParityCheckpoint,
    LiveHeldPlanetParityRecorder,
    capture_live_held_planet_parity_checkpoint,
    compare_captured_live_held_planet,
    headless_held_planet_run_from_checkpoint,
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


def _snapshot(sequence, *, planet=True, level=1, phase="SELECTING_HAND"):
    consumables = [_planet()] if planet else []
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
            "jokers": {"limit": 5, "count": 0, "cards": []},
            "consumables": {
                "limit": 2,
                "count": len(consumables),
                "cards": consumables,
            },
            "hands": {"High Card": {"level": level}},
            "last_tarot_planet": "c_pluto" if level > 1 else None,
        },
    )


def _usage(pluto=0):
    return LiveConsumableUsageState(
        counts={"c_pluto": pluto} if pluto else {},
        sets={"c_pluto": "Planet"} if pluto else {},
        totals={
            "tarot": 0,
            "planet": pluto,
            "spectral": 0,
            "tarot_planet": pluto,
            "all": pluto,
        },
    )


def _action():
    return BalatroAction(
        USE_CONSUMABLE,
        target=SimpleNamespace(area_index=2, name="Pluto", label="Pluto"),
    )


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, pluto=0):
        game = {}
        self.tables = {100: game}
        if pluto:
            game.update(
                {
                    "consumeable_usage": _lua("table", 200),
                    "consumeable_usage_total": _lua("table", 400),
                }
            )
            self.tables[200] = {"c_pluto": _lua("table", 300)}
            self.tables[300] = {
                "count": _lua("number", float(pluto)),
                "order": _lua("number", 1.0),
                "set": _lua("string", "Planet"),
            }
            self.tables[400] = {
                "tarot": _lua("number", 0.0),
                "planet": _lua("number", float(pluto)),
                "spectral": _lua("number", 0.0),
                "tarot_planet": _lua("number", float(pluto)),
                "all": _lua("number", float(pluto)),
            }

    def string_fields(self, address):
        return dict(self.tables[address])


class _Observer:
    def __init__(self):
        self.snapshot = _snapshot(1)
        self.decoder = _Decoder()

    def observe(self):
        return deepcopy(self.snapshot)

    def _root(self):
        return self.decoder, 0, {"GAME": _lua("table", 100)}


def test_env_r5_exact_planet_owner_admits_selecting_hand_without_phase_change():
    checkpoint = LiveHeldPlanetParityCheckpoint(_snapshot(1), _usage())
    run = headless_held_planet_run_from_checkpoint(checkpoint)
    hand_type = run.public.consumables[0].hand_type

    assert can_use_planet_exact(run, 0) is True
    result, evidence = use_planet_with_public_evidence(run, consumable_index=0)

    assert evidence.before.phase == "SELECTING_HAND"
    assert evidence.after.phase == "SELECTING_HAND"
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.consumables == []
    assert result.public.hand_levels[hand_type] == 2
    assert result.public.last_tarot_planet == "c_pluto"
    assert result.consumable_usage_counts == {"c_pluto": 1}
    assert result.consumable_usage_totals["planet"] == 1


def test_env_r5_held_planet_selecting_hand_comparison_accepts_first_use_set_creation():
    comparison = compare_captured_live_held_planet(
        LiveHeldPlanetParityCheckpoint(_snapshot(1), _usage()),
        _action(),
        _snapshot(2, planet=False, level=2),
        _usage(1),
    )

    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_held_planet_capture_can_explicitly_checkpoint_selecting_hand():
    checkpoint = capture_live_held_planet_parity_checkpoint(
        _Observer(),
        expected_phase="SELECTING_HAND",
    )

    assert checkpoint.public_snapshot.phase == "SELECTING_HAND"
    assert checkpoint.usage == _usage()


def test_env_r5_held_planet_recorder_uses_planned_selecting_hand_phase(tmp_path):
    observer = _Observer()
    action = _action()
    decision = SimpleNamespace(snapshot=deepcopy(observer.snapshot), action=action)
    recorder = LiveHeldPlanetParityRecorder("attempt-001", observer, directory=tmp_path)

    before = recorder.capture_before(decision)
    after = _snapshot(2, planet=False, level=2)
    observer.snapshot = after
    observer.decoder = _Decoder(1)
    dispatch = LiveInjectedActionResult(action, decision.snapshot, after)
    comparison = recorder.record_after(before, decision, dispatch)

    assert comparison.matches is True
    assert recorder.path.is_file()


def test_env_r5_exact_planet_owner_still_rejects_unowned_phase():
    checkpoint = LiveHeldPlanetParityCheckpoint(
        _snapshot(1, phase="BLIND_SELECT"),
        _usage(),
    )

    with pytest.raises(LiveHeldPlanetParityCaptureError, match="checkpoint phase"):
        headless_held_planet_run_from_checkpoint(checkpoint)
