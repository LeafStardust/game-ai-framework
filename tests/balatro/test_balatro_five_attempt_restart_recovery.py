from types import SimpleNamespace

from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
    _recover_restart_boundary,
)
from games.balatro.live.runtime.live_memory_restart_run_injected import LiveRunRestartError


class _Control:
    def __init__(self):
        self.stopped = False
        self.telemetry = []

    def stop_requested(self):
        return self.stopped

    def request_stop(self):
        self.stopped = True

    def write_telemetry(self, activity, **data):
        self.telemetry.append((activity, data))


def _snapshot(phase, *, deck="RED", stake="WHITE", marker=1):
    return SimpleNamespace(
        phase=phase,
        state_complete=True,
        sequence=marker,
        payload={"deck": deck, "stake": stake, "marker": marker},
    )


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.index = 0

    def observe(self):
        if self.index < len(self.snapshots):
            value = self.snapshots[self.index]
            self.index += 1
            return value
        return self.snapshots[-1]


def test_restart_boundary_accepts_already_settled_blind_select_without_second_restart():
    settled = _snapshot("BLIND_SELECT", marker=2)
    runner = SimpleNamespace(observer=_Observer([settled, settled, settled]))

    assert _recover_restart_boundary(
        runner,
        "RED",
        "WHITE",
        stop_requested=lambda: False,
        timeout_seconds=0.1,
        poll_seconds=0.0,
        stable_confirmations=3,
    ) == "READY"


def test_restart_boundary_allows_retry_only_while_same_loss_game_over_is_authoritative():
    runner = SimpleNamespace(observer=_Observer([_snapshot("GAME_OVER")]))

    assert _recover_restart_boundary(
        runner,
        "RED",
        "WHITE",
        stop_requested=lambda: False,
        timeout_seconds=0.0,
        poll_seconds=0.0,
    ) == "GAME_OVER"


def test_bounded_supervisor_retries_transient_restart_when_game_over_remains():
    control = _Control()
    calls = []

    def restart(_runner, _deck, _stake):
        calls.append(1)
        if len(calls) == 1:
            raise LiveRunRestartError("transient restart rejection")
        return "restarted"

    supervisor = BoundedBalatroAgentSupervisor(
        control=control,
        restart_run=restart,
        restart_recovery_attempts=3,
    )
    runner = SimpleNamespace(observer=_Observer([_snapshot("GAME_OVER")]))

    assert supervisor.restart_run(runner, "RED", "WHITE") == "restarted"
    assert len(calls) == 2
    assert any(activity == "RESTART_RETRYING" for activity, _ in control.telemetry)


def test_bounded_supervisor_does_not_double_restart_after_game_already_left_game_over():
    control = _Control()
    calls = []

    def restart(_runner, _deck, _stake):
        calls.append(1)
        raise LiveRunRestartError(
            "restart did not reach a sustained settled same-deck/stake BLIND_SELECT checkpoint before timeout"
        )

    settled = _snapshot("BLIND_SELECT", marker=9)
    runner = SimpleNamespace(observer=_Observer([settled, settled, settled]))
    supervisor = BoundedBalatroAgentSupervisor(
        control=control,
        restart_run=restart,
        restart_recovery_attempts=3,
    )

    assert supervisor.restart_run(runner, "RED", "WHITE") is None
    assert len(calls) == 1
    assert any(activity == "RESTART_RECOVERED" for activity, _ in control.telemetry)
