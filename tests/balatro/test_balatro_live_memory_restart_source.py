from types import SimpleNamespace

import pytest

from games.balatro.live.runtime.live_memory_restart_run_injected import (
    LiveRunRestartError,
    _validate_restart_source,
)


def _snapshot(*, phase="GAME_OVER", state_complete=True, won=False):
    return SimpleNamespace(
        phase=phase,
        state_complete=state_complete,
        payload={"deck": "RED", "stake": "WHITE", "won": won},
    )


def test_game_over_restart_source_ignores_sticky_won_bit():
    assert _validate_restart_source(_snapshot(won=True)) == ("RED", "WHITE")


def test_restart_source_still_requires_complete_game_over():
    with pytest.raises(LiveRunRestartError, match="requires GAME_OVER"):
        _validate_restart_source(_snapshot(phase="ROUND_EVAL", won=True))

    with pytest.raises(LiveRunRestartError, match="not complete"):
        _validate_restart_source(_snapshot(state_complete=False, won=True))
