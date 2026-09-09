import json
from types import SimpleNamespace

from games.balatro.actions import SKIP_BLIND, BalatroAction
from games.balatro.live.injected.hand_dispatcher import LiveInjectedActionResult
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence, *, blind_type="SMALL"):
    return LiveBalatroSnapshot(
        sequence,
        "BLIND_SELECT",
        True,
        {"deck": "RED", "stake": "WHITE", "blind": {"type": blind_type}},
    )


def test_env_r5_supervisor_blind_skip_capture_is_observational_only(
    tmp_path, monkeypatch
):
    import games.balatro.live.runtime.balatro_agent_supervisor_entry as entry

    before = _snapshot(1)
    after = _snapshot(2, blind_type="BIG")
    action = BalatroAction(SKIP_BLIND)
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
                differences=("private.skips.after",),
            )

    monkeypatch.setattr(entry, "StrategyAwareLiveMemoryInjectedSingleStepRunner", FakeRunner)
    monkeypatch.setattr(entry, "_validated_supervisor_bridge", lambda: object())
    monkeypatch.setattr(entry, "LiveBlindSkipParityRecorder", FakeRecorder)
    diagnostic_dir = tmp_path / "diagnostics"
    runner = entry._diagnostic_runner_factory(
        object(),
        control=FakeControl(),
        session_id="session-r5",
        diagnostic_directory=str(diagnostic_dir),
        blind_skip_parity_directory=str(tmp_path / "private"),
    )

    assert runner.execute(decision) is execution
    assert runner.executions == 1
    assert FakeRecorder.instances[0].run_id == "attempt-001"
    diagnostic = json.loads(
        (diagnostic_dir / "session-r5.jsonl").read_text(encoding="utf-8")
    )
    assert diagnostic["stage"] == "blind_skip_parity_mismatch"
    assert diagnostic["data"]["differences"] == ["private.skips.after"]
