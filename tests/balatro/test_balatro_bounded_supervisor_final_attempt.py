from __future__ import annotations

from games.balatro.live.runtime.agent_control import BalatroAgentControl
from games.balatro.live.runtime.balatro_agent_bounded_supervisor import (
    BoundedBalatroAgentSupervisor,
)


def test_final_bounded_attempt_never_issues_another_restart(tmp_path) -> None:
    control = BalatroAgentControl(tmp_path / "control")
    calls: list[tuple[str, str]] = []

    def restart(_runner, deck: str, stake: str):
        calls.append((deck, stake))
        raise AssertionError("restart must not run after the final bounded attempt")

    supervisor = BoundedBalatroAgentSupervisor(
        control=control,
        restart_run=restart,
        max_attempts=3,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
    )
    supervisor._attempts = [object(), object(), object()]

    result = supervisor.restart_run(object(), "RED", "WHITE")

    assert result is None
    assert calls == []
    assert control.stop_requested()
