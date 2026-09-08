import threading
import time

import pytest

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeTimeoutError,
)


def test_timeout_cancels_exact_still_pending_command(tmp_path):
    bridge = FirstPartyBalatroBridge(
        bridge_dir=tmp_path,
        timeout=0.0,
        poll_interval=0.0,
    )

    with pytest.raises(
        InjectedBridgeTimeoutError,
        match="still-pending command was cancelled",
    ):
        bridge.status()

    assert bridge.command_path.exists() is False
    assert bridge.response_path.exists() is False


def test_timeout_reports_indeterminate_if_balatro_already_consumed_slot(tmp_path):
    bridge = FirstPartyBalatroBridge(
        bridge_dir=tmp_path,
        timeout=0.05,
        poll_interval=0.001,
    )

    consumed = threading.Event()

    def consume_without_response():
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if bridge.command_path.exists():
                bridge.command_path.unlink()
                consumed.set()
                return
            time.sleep(0.001)

    worker = threading.Thread(target=consume_without_response)
    worker.start()
    try:
        with pytest.raises(
            InjectedBridgeTimeoutError,
            match="outcome is indeterminate",
        ):
            bridge.status()
    finally:
        worker.join(timeout=1.0)

    assert consumed.is_set()
    assert bridge.command_path.exists() is False
