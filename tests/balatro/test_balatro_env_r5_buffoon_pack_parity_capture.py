from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.buffoon_pack_parity_capture import (
    LiveBuffoonPackParityCaptureError,
    LiveBuffoonPackParityCheckpoint,
    LiveBuffoonPackParityRecorder,
    buffoon_pack_parity_checkpoint_from_payload,
    buffoon_pack_parity_checkpoint_to_payload,
    capture_live_buffoon_pack_parity_checkpoint,
    compare_captured_live_buffoon_pack,
    headless_buffoon_pack_run_from_checkpoint,
)
from games.balatro.live.injected.hand_dispatcher import LiveInjectedActionResult
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.luajit_memory import LuaValue


def _choice(*, label="Joker", center="j_joker", live_id=20):
    return {
        "ability_name": label,
        "ability_set": "Joker",
        "center": center,
        "label": label,
        "live_id": live_id,
        "area_index": 0,
        "rarity": "COMMON",
        "debuff": False,
        "eternal": False,
    }


def _snapshot(sequence, phase, *, jokers=()):
    return LiveBalatroSnapshot(
        sequence,
        phase,
        True,
        {
            "deck": "RED",
            "stake": "WHITE",
            "money": 12,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 0},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "count": len(jokers), "cards": list(jokers)},
            "consumables": {"limit": 2, "cards": []},
        },
    )


def _checkpoint(*, choice=None, choices_remaining=1, return_phase="SHOP"):
    return LiveBuffoonPackParityCheckpoint(
        public_snapshot=_snapshot(1, "BUFFOON_PACK"),
        choices_remaining=choices_remaining,
        return_phase=return_phase,
        choices=(choice or _choice(),),
    )


def _select_action(choice=None):
    choice = choice or _choice()
    return BalatroAction(
        SELECT_PACK_CARD,
        target=SimpleNamespace(
            area_index=0,
            label=choice["label"],
            live_id=choice["live_id"],
            data=deepcopy(choice),
        ),
    )


def test_env_r5_final_buffoon_choice_replays_exact_public_transition():
    choice = _choice()
    comparison = compare_captured_live_buffoon_pack(
        _checkpoint(choice=choice),
        _select_action(choice),
        _snapshot(2, "SHOP", jokers=(choice,)),
    )

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.simulator.action_id == SELECT_PACK_CARD
    assert comparison.public.simulator.action_params == (("option_index", 0),)


def test_env_r5_final_buffoon_skip_replays_exact_public_transition():
    comparison = compare_captured_live_buffoon_pack(
        _checkpoint(),
        BalatroAction(SKIP_BOOSTER),
        _snapshot(2, "SHOP"),
    )

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.simulator.action_id == SKIP_BOOSTER


@pytest.mark.parametrize(
    ("checkpoint", "message"),
    [
        (_checkpoint(choices_remaining=2), "one remaining pick"),
        (_checkpoint(choice=_choice(label="Juggler", center="j_juggler")), "inventory-only"),
        (_checkpoint(choice=_choice(live_id=None)), "live_id"),
        (_checkpoint(return_phase="ROUND_EVAL"), "return origin"),
    ],
)
def test_env_r5_buffoon_checkpoint_fails_closed_outside_exact_subset(
    checkpoint,
    message,
):
    with pytest.raises(LiveBuffoonPackParityCaptureError, match=message):
        headless_buffoon_pack_run_from_checkpoint(checkpoint)


def test_env_r5_buffoon_choice_requires_captured_live_identity():
    choice = _choice()
    action = _select_action(choice)
    action.target.data["center"] = "j_misprint"

    with pytest.raises(LiveBuffoonPackParityCaptureError, match="center"):
        compare_captured_live_buffoon_pack(
            _checkpoint(choice=choice),
            action,
            _snapshot(2, "SHOP", jokers=(choice,)),
        )


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self):
        self.tables = {
            100: {
                "pack_choices": _lua("number", 1.0),
                "PACK_INTERRUPT": _lua("number", 10.0),
            },
            200: {
                "SHOP": _lua("number", 10.0),
                "BLIND_SELECT": _lua("number", 11.0),
            },
            300: {"cards": _lua("table", 350)},
        }

    def string_fields(self, address):
        return dict(self.tables[address])

    def array_items_strict(self, address):
        assert address == 350
        return [(1, _lua("table", 400))]


class _Observer:
    def __init__(self):
        self.snapshot = _snapshot(1, "BUFFOON_PACK")
        self.decoder = _Decoder()

    def observe(self):
        return deepcopy(self.snapshot)

    def _root(self):
        return self.decoder, 0, {
            "GAME": _lua("table", 100),
            "STATES": _lua("table", 200),
            "pack_cards": _lua("table", 300),
        }


def test_env_r5_buffoon_capture_reads_stable_final_pack_authority(monkeypatch):
    import games.balatro.live.buffoon_pack_parity_capture as capture

    monkeypatch.setattr(capture, "_normalize_item", lambda *_args, **_kwargs: _choice())

    checkpoint = capture_live_buffoon_pack_parity_checkpoint(_Observer())

    assert checkpoint.choices_remaining == 1
    assert checkpoint.return_phase == "SHOP"
    assert checkpoint.choices == (_choice(),)


def test_env_r5_buffoon_checkpoint_payload_roundtrip():
    checkpoint = _checkpoint()
    assert buffoon_pack_parity_checkpoint_from_payload(
        buffoon_pack_parity_checkpoint_to_payload(checkpoint)
    ) == checkpoint


def test_env_r5_buffoon_recorder_preserves_private_checkpoint(tmp_path, monkeypatch):
    import games.balatro.live.buffoon_pack_parity_capture as capture

    monkeypatch.setattr(capture, "_normalize_item", lambda *_args, **_kwargs: _choice())
    observer = _Observer()
    action = _select_action()
    decision = SimpleNamespace(snapshot=observer.snapshot, action=action)
    recorder = LiveBuffoonPackParityRecorder("attempt-001", observer, directory=tmp_path)
    before = recorder.capture_before(decision)
    after = _snapshot(2, "SHOP", jokers=(_choice(),))
    observer.snapshot = after
    dispatch = LiveInjectedActionResult(action, decision.snapshot, after)

    comparison = recorder.record_after(before, decision, dispatch)

    assert comparison.matches is True
    assert recorder.path.exists()
    row = recorder.path.read_text(encoding="utf-8")
    assert '"schema":"balatro-r5-buffoon-pack-parity-v1"' in row
    assert '"option_index":0' in row


def test_env_r5_supervisor_buffoon_capture_is_observational_only(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    before = _snapshot(1, "BUFFOON_PACK")
    after = _snapshot(2, "SHOP", jokers=(_choice(),))
    action = _select_action()
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
            return SimpleNamespace(matches=False, differences=("public.after",))

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveBuffoonPackParityRecorder", FakeRecorder)
    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        buffoon_pack_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    assert FakeRecorder.instances[0].run_id == "attempt-001"
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "buffoon_pack_parity_mismatch"
    assert diagnostic["data"]["differences"] == ["public.after"]
