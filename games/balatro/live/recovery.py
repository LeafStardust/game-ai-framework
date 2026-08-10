import time

from games.balatro.live.balatrobot_bridge import (
    BalatroBotBridge,
    BalatroBotConnectionError,
    BalatroBotRpcError,
)
from games.balatro.live.protocol import (
    LiveBalatroCommand,
    LiveBalatroSnapshot,
)


class BalatroLiveRecovery:
    """Recovers live state without replaying uncertain mutations."""

    INVALID_STATE = -32002

    def __init__(
        self,
        bridge: BalatroBotBridge,
        connection_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        self.bridge = bridge
        self.connection_retries = max(0, connection_retries)
        self.retry_delay = max(0.0, retry_delay)

    def observe(self) -> LiveBalatroSnapshot:
        attempts = self.connection_retries + 1

        for attempt in range(attempts):
            try:
                return self.bridge.observe()
            except BalatroBotConnectionError:
                if attempt == attempts - 1:
                    raise
                self._sleep()

        raise RuntimeError("unreachable")

    def send(
        self,
        command: LiveBalatroCommand,
    ) -> LiveBalatroSnapshot:
        try:
            self.bridge.send(command)
        except BalatroBotConnectionError:
            return self.observe()
        except BalatroBotRpcError as error:
            if error.code != self.INVALID_STATE:
                raise
            return self.observe()

        return self.observe()

    def request(
        self,
        method: str,
        params: dict | None = None,
    ) -> LiveBalatroSnapshot:
        try:
            return self.bridge.request(method, params)
        except BalatroBotConnectionError:
            return self.observe()
        except BalatroBotRpcError as error:
            if error.code != self.INVALID_STATE:
                raise
            return self.observe()

    def _sleep(self) -> None:
        if self.retry_delay > 0:
            time.sleep(self.retry_delay)
