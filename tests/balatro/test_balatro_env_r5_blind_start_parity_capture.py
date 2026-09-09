import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import SELECT_BLIND, BalatroAction
from games.balatro.live.blind_start_parity_capture import (
    LiveBlindStartParityCaptureError,
    LiveBlindStartParityRecorder,
    blind_start_parity_checkpoint_from_payload,
    blind_start_parity_checkpoint_to_payload,
)
from games.balatro.live.blind_start_parity_checkpoint import (
    LiveBlindStartParityCheckpoint,
)
from games.balatro.live.injected.hand_dispatcher import LiveInjectedActionResult
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, phase="BLIND_SELECT"):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"deck": "RED", "stake": "WHITE", "money": 4},
    )


def _checkpoint(sequence, phase="BLIND_SELECT"):
    return LiveBlindStartParityCheckpoint(
        public_snapshot=_snapshot(sequence, phase),
        rng_snapshot={"seed": "R5-BLIND", "nodes": {"nr1": "0x1.0p-1"}},
        active_tag_count=0,
    )


def _decision(snapshot=None, action=None):
    return SimpleNamespace(
        snapshot=snapshot or _snapshot(1),
        action=action or BalatroAction(SELECT_BLIND),
    )


def test_env_r5_blind_start_checkpoint_payload_roundtrip_preserves_private_authority():
    checkpoint = _checkpoint(7)

    restored = blind_start_parity_checkpoint_from_payload(
        blind_start_parity_checkpoint_to_payload(checkpoint)
    )

    assert restored == checkpoint
    assert restored.rng_snapshot is not checkpoint.rng_snapshot
    assert restored.public_snapshot.payload is not checkpoint.public_snapshot.payload


@pytest.mark.parametrize(
    "action,match",
    [
        (BalatroAction("PLAY_CARDS"), "only accepts SELECT_BLIND"),
        (BalatroAction(SELECT_BLIND, cards=[object()]), "must not select cards"),
        (BalatroAction(SELECT_BLIND, target=0), "must be parameterless"),
    ],
)
def test_env_r5_blind_start_recorder_rejects_noncanonical_actions(
    tmp_path,
    action,
    match,
):
    recorder = LiveBlindStartParityRecorder("run-1", object(), directory=tmp_path)

    with pytest.raises(LiveBlindStartParityCaptureError, match=match):
        recorder.capture_before(_decision(action=action))


def test_env_r5_blind_start_recorder_writes_verdict_and_resumes_sequence(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.blind_start_parity_capture as capture

    before = _checkpoint(1)
    after = _checkpoint(2, "SELECTING_HAND")
    checkpoints = iter((before, after))
    monkeypatch.setattr(
        capture,
        "capture_live_blind_start_parity_checkpoint",
        lambda observer, *, expected_phase: next(checkpoints),
    )
    comparison = SimpleNamespace(
        matches=True,
        differences=(),
        public=SimpleNamespace(matches=True, differences=()),
    )
    monkeypatch.setattr(
        capture,
        "compare_captured_live_blind_start",
        lambda first, second: comparison,
    )

    recorder = LiveBlindStartParityRecorder("run-1", object(), directory=tmp_path)
    decision = _decision(before.public_snapshot)
    pending = recorder.capture_before(decision)
    dispatch = LiveInjectedActionResult(
        action=decision.action,
        before=before.public_snapshot,
        after=after.public_snapshot,
    )

    assert recorder.record_after(pending, decision, dispatch) is comparison
    row = json.loads(recorder.path.read_text(encoding="utf-8"))
    assert row["schema"] == "balatro-r5-blind-start-parity-v1"
    assert row["run_id"] == "run-1"
    assert row["sequence"] == 1
    assert row["action"] == SELECT_BLIND
    assert row["before"]["rng_snapshot"] == before.rng_snapshot
    assert row["after"]["rng_snapshot"] == after.rng_snapshot
    assert row["comparison"] == {
        "matches": True,
        "differences": [],
        "public_matches": True,
        "public_differences": [],
    }
    assert LiveBlindStartParityRecorder(
        "run-1",
        object(),
        directory=tmp_path,
    ).sequence == 1


def test_env_r5_blind_start_recorder_rejects_post_checkpoint_drift(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.blind_start_parity_capture as capture

    before = _checkpoint(1)
    drifted = _checkpoint(3, "SELECTING_HAND")
    checkpoints = iter((before, drifted))
    monkeypatch.setattr(
        capture,
        "capture_live_blind_start_parity_checkpoint",
        lambda observer, *, expected_phase: next(checkpoints),
    )
    recorder = LiveBlindStartParityRecorder("run-1", object(), directory=tmp_path)
    decision = _decision(before.public_snapshot)
    pending = recorder.capture_before(decision)
    dispatch = LiveInjectedActionResult(
        action=decision.action,
        before=before.public_snapshot,
        after=_snapshot(2, "SELECTING_HAND"),
    )

    with pytest.raises(LiveBlindStartParityCaptureError, match="post-start checkpoint"):
        recorder.record_after(pending, decision, dispatch)
    assert not recorder.path.exists()


def test_env_r5_supervisor_blind_start_mismatch_is_observational_only(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    before = _snapshot(1)
    after = _snapshot(2, "SELECTING_HAND")
    decision = _decision(before)
    dispatch = LiveInjectedActionResult(decision.action, before, after)
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
            return SimpleNamespace(matches=False, differences=("rng.after",))

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveBlindStartParityRecorder", FakeRecorder)
    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        blind_start_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    assert FakeRecorder.instances[0].run_id == "attempt-001"
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "blind_start_parity_mismatch"
    assert diagnostic["data"]["differences"] == ["rng.after"]


def test_env_r5_supervisor_blind_start_capture_failure_does_not_block_action(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    decision = _decision()
    execution = (object(), {})

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            self.executions = 0

        def decide(self):
            raise AssertionError("not used")

        def execute(self, received):
            self.executions += 1
            return execution

    class FakeControl:
        def read_status(self):
            return {"run_id": "attempt-002", "state": "RUNNING"}

    class FailingRecorder:
        def __init__(self, *args, **kwargs):
            pass

        def capture_before(self, received):
            raise RuntimeError("private capture unavailable")

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveBlindStartParityRecorder", FailingRecorder)
    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        blind_start_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "blind_start_parity_capture_before"
