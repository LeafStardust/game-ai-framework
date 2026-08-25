from games.balatro.live.runtime import balatro_agent_three_attempts_entry as entry
from games.balatro.live.runtime import balatro_agent_three_attempts_toggle as toggle
from games.balatro.live.runtime import balatro_agent_toggle as base_toggle
from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
)


def test_three_attempt_supervisor_sets_exact_attempt_cap(monkeypatch):
    captured = {}

    def fake_init(self, *args, **kwargs):
        del self, args
        captured.update(kwargs)

    monkeypatch.setattr(BoundedBalatroAgentSupervisor, "__init__", fake_init)

    entry.ThreeAttemptBalatroAgentSupervisor()

    assert captured["max_attempts"] == 3
    assert captured["restart_run"] is entry._three_attempt_restart


def test_three_attempt_toggle_consumes_batch_selector():
    argv = ["toggle", "--three", "--status"]

    toggle._strip_selector(argv)

    assert argv == ["toggle", "--status"]


def test_importing_three_attempt_toggle_does_not_mutate_canonical_launcher():
    assert base_toggle.SUPERVISOR_MODULE.endswith("balatro_agent_supervisor_entry")
