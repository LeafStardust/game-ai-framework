import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import REFRESH_SHOP, BalatroAction
from games.balatro.live.injected.hand_dispatcher import LiveInjectedActionResult
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.reroll_parity_capture import (
    LiveRerollParityCaptureError,
    LiveRerollParityRecorder,
    reroll_parity_checkpoint_from_payload,
    reroll_parity_checkpoint_to_payload,
)
from games.balatro.live.reroll_parity_checkpoint import LiveRerollParityCheckpoint
from games.balatro.live.runtime.live_memory_shop_terms import LiveShopRerollTerms


def _snapshot(sequence, money=20):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={"money": money, "vouchers_observed": True, "vouchers": []},
    )


def _checkpoint(sequence, money=20):
    return LiveRerollParityCheckpoint(
        public_snapshot=_snapshot(sequence, money),
        rng_snapshot={"seed": "R5-CAPTURE", "counters": {"shop": sequence}},
        reroll_terms=LiveShopRerollTerms(cost=4 + sequence, free_rerolls=0),
        active_tag_count=0,
    )


def _decision(snapshot=None, action=None):
    return SimpleNamespace(
        snapshot=snapshot or _snapshot(1),
        action=action or BalatroAction(REFRESH_SHOP),
    )


def test_env_r5_reroll_parity_checkpoint_payload_roundtrip_preserves_private_authority():
    checkpoint = _checkpoint(7, money=31)

    restored = reroll_parity_checkpoint_from_payload(
        reroll_parity_checkpoint_to_payload(checkpoint)
    )

    assert restored == checkpoint
    assert restored.rng_snapshot is not checkpoint.rng_snapshot
    assert restored.public_snapshot.payload is not checkpoint.public_snapshot.payload


@pytest.mark.parametrize(
    "action,match",
    [
        (BalatroAction("PLAY_CARDS"), "only accepts REFRESH_SHOP"),
        (BalatroAction(REFRESH_SHOP, cards=[object()]), "must not select cards"),
        (BalatroAction(REFRESH_SHOP, target=0), "must be parameterless"),
    ],
)
def test_env_r5_reroll_parity_recorder_rejects_noncanonical_refresh_actions(
    tmp_path,
    action,
    match,
):
    recorder = LiveRerollParityRecorder("run-1", object(), directory=tmp_path)

    with pytest.raises(LiveRerollParityCaptureError, match=match):
        recorder.capture_before(_decision(action=action))


def test_env_r5_reroll_parity_recorder_writes_private_verdict_and_resumes_sequence(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.reroll_parity_capture as capture

    before = _checkpoint(1, money=20)
    after = _checkpoint(2, money=15)
    checkpoints = iter((before, after))
    monkeypatch.setattr(
        capture,
        "capture_live_reroll_parity_checkpoint",
        lambda observer: next(checkpoints),
    )
    comparison = SimpleNamespace(
        matches=True,
        differences=(),
        public=SimpleNamespace(matches=True, differences=()),
    )
    monkeypatch.setattr(
        capture,
        "compare_captured_live_reroll",
        lambda first, second: comparison,
    )

    recorder = LiveRerollParityRecorder("run-1", object(), directory=tmp_path)
    decision = _decision(before.public_snapshot)
    pending = recorder.capture_before(decision)
    dispatch = LiveInjectedActionResult(
        action=decision.action,
        before=before.public_snapshot,
        after=after.public_snapshot,
    )

    assert recorder.record_after(pending, decision, dispatch) is comparison
    row = json.loads(recorder.path.read_text(encoding="utf-8"))
    assert row["schema"] == "balatro-r5-reroll-parity-v1"
    assert row["run_id"] == "run-1"
    assert row["sequence"] == 1
    assert row["action"] == REFRESH_SHOP
    assert row["before"]["rng_snapshot"] == before.rng_snapshot
    assert row["after"]["rng_snapshot"] == after.rng_snapshot
    assert row["comparison"] == {
        "matches": True,
        "differences": [],
        "public_matches": True,
        "public_differences": [],
    }

    resumed = LiveRerollParityRecorder("run-1", object(), directory=tmp_path)
    assert resumed.sequence == 1


def test_env_r5_reroll_parity_recorder_rejects_post_checkpoint_drift(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.reroll_parity_capture as capture

    before = _checkpoint(1, money=20)
    drifted_after = _checkpoint(3, money=14)
    checkpoints = iter((before, drifted_after))
    monkeypatch.setattr(
        capture,
        "capture_live_reroll_parity_checkpoint",
        lambda observer: next(checkpoints),
    )

    recorder = LiveRerollParityRecorder("run-1", object(), directory=tmp_path)
    decision = _decision(before.public_snapshot)
    pending = recorder.capture_before(decision)
    dispatch = LiveInjectedActionResult(
        action=decision.action,
        before=before.public_snapshot,
        after=_snapshot(2, money=15),
    )

    with pytest.raises(LiveRerollParityCaptureError, match="post-reroll checkpoint"):
        recorder.record_after(pending, decision, dispatch)
    assert not recorder.path.exists()


def test_env_r5_supervisor_entry_parity_mismatch_is_observational_only(
    tmp_path,
    monkeypatch,
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    before = _snapshot(1, money=20)
    after = _snapshot(2, money=15)
    decision = _decision(before)
    dispatch = LiveInjectedActionResult(
        action=decision.action,
        before=before,
        after=after,
    )
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
            self.before_calls = 0
            self.after_calls = 0
            self.__class__.instances.append(self)

        def capture_before(self, received):
            assert received is decision
            self.before_calls += 1
            return "private-before"

        def record_after(self, pending, received, result):
            assert pending == "private-before"
            assert received is decision
            assert result is dispatch
            self.after_calls += 1
            return SimpleNamespace(matches=False, differences=("rng.after",))

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveRerollParityRecorder", FakeRecorder)

    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        reroll_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    assert len(FakeRecorder.instances) == 1
    assert FakeRecorder.instances[0].run_id == "attempt-001"
    assert FakeRecorder.instances[0].before_calls == 1
    assert FakeRecorder.instances[0].after_calls == 1
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "reroll_parity_mismatch"
    assert diagnostic["data"]["differences"] == ["rng.after"]


def test_env_r5_supervisor_entry_parity_capture_failure_does_not_block_refresh(
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
            raise RuntimeError("private memory unavailable")

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveRerollParityRecorder", FailingRecorder)

    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5-failure",
        diagnostic_directory=str(diagnostic_dir),
        reroll_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5-failure.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "reroll_parity_capture_before"
    assert diagnostic["data"]["error"] == "private memory unavailable"
