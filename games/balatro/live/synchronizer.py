import time

from games.balatro.live.interfaces import BalatroLiveBridge
from games.balatro.live.protocol import LiveBalatroSnapshot


class BalatroLiveSynchronizer:

    def __init__(
        self,
        bridge: BalatroLiveBridge,
        poll_interval: float = 0.05,
        timeout: float = 10.0,
    ):
        self.bridge = bridge
        self.poll_interval = poll_interval
        self.timeout = timeout

    def wait_for_ready(
        self,
        after_sequence: int = -1,
        phases: set[str] | None = None,
        *,
        require_complete: bool = True,
    ) -> LiveBalatroSnapshot:
        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            if not self.bridge.is_connected():
                self._sleep()
                continue

            snapshot = self.bridge.observe()

            if snapshot.sequence <= after_sequence:
                self._sleep()
                continue

            if require_complete and not snapshot.state_complete:
                self._sleep()
                continue

            if phases is not None and snapshot.phase not in phases:
                self._sleep()
                continue

            return snapshot

        raise TimeoutError(
            "timed out waiting for a stable Balatro state"
        )

    def wait_for_change(
        self,
        snapshot: LiveBalatroSnapshot,
        phases: set[str] | None = None,
        *,
        require_complete: bool = True,
    ) -> LiveBalatroSnapshot:
        return self.wait_for_ready(
            after_sequence=snapshot.sequence,
            phases=phases,
            require_complete=require_complete,
        )

    def _sleep(self) -> None:
        if self.poll_interval > 0:
            time.sleep(self.poll_interval)
