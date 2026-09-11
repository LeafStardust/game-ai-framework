import time

import pytest

from games.balatro.live.runtime.process_memory import (
    BalatroProcessMemoryError,
    WindowsProcessMemoryReader,
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


def test_live_reader_uses_direct_read_by_default(monkeypatch):
    reader = object.__new__(WindowsProcessMemoryReader)
    reader.handle = 1
    reader._read_once = lambda address, size: b"direct"

    def unexpected_worker(*args, **kwargs):
        raise AssertionError("normal live reads must not spawn a worker")

    monkeypatch.setattr(
        "games.balatro.live.runtime.process_memory._run_with_process_timeout",
        unexpected_worker,
    )

    assert reader.read(0x1000, 6) == b"direct"
