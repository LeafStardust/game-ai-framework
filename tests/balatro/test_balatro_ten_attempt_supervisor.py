from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
)


class _Control:
    def __init__(self):
        self.stop_requests = 0

    def request_stop(self):
        self.stop_requests += 1


class _Attempt:
    outcome = "LOSS"


def test_tenth_completed_attempt_suppresses_attempt_eleven_restart():
    control = _Control()
    restart_calls = []
    supervisor = BoundedBalatroAgentSupervisor(
        control=control,
        restart_run=lambda runner, deck, stake: restart_calls.append((runner, deck, stake)),
        max_attempts=10,
    )
    supervisor._attempts[:] = [_Attempt() for _ in range(10)]

    assert supervisor.restart_run(object(), "RED", "WHITE") is None
    assert restart_calls == []
    assert control.stop_requests == 1


def test_restart_still_occurs_before_attempt_cap():
    control = _Control()
    restart_calls = []
    supervisor = BoundedBalatroAgentSupervisor(
        control=control,
        restart_run=lambda runner, deck, stake: restart_calls.append((runner, deck, stake)) or "ok",
        max_attempts=10,
    )
    supervisor._attempts[:] = [_Attempt() for _ in range(9)]

    assert supervisor.restart_run("runner", "RED", "WHITE") == "ok"
    assert restart_calls == [("runner", "RED", "WHITE")]
    assert control.stop_requests == 0
