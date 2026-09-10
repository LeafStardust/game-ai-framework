import time

import pytest

from games.balatro.live.runtime.process_memory import (
    BalatroProcessMemoryError,
    _run_with_process_timeout,
    _sleep_for_test,
)


def test_run_with_process_timeout_terminates_hanging_work():
    start = time.monotonic()

    with pytest.raises(BalatroProcessMemoryError, match="timed out"):
        _run_with_process_timeout(
            _sleep_for_test,
            timeout_seconds=0.1,
            args=(2.0,),
        )

    elapsed = time.monotonic() - start
    assert elapsed < 1.0


def test_run_with_process_timeout_returns_fast_worker_result():
    assert _run_with_process_timeout(
        _sleep_for_test,
        timeout_seconds=1.0,
        args=(0.0,),
    ) is None
