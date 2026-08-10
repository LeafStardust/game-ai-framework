import time

from games.balatro.live.balatrobot_bridge import (
    BalatroBotBridge,
    BalatroBotRpcError,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class BalatroLiveLifecycle:

    SELECT_NOT_READY_ERRORS = (
        "no blind on deck",
        "blind pane not found",
        "select button not found",
    )

    def __init__(
        self,
        bridge: BalatroBotBridge,
        select_retries: int = 40,
        select_retry_delay: float = 0.05,
    ):
        self.bridge = bridge
        self.select_retries = max(0, select_retries)
        self.select_retry_delay = max(0.0, select_retry_delay)

    def start_run(
        self,
        deck: str = "RED",
        stake: str = "WHITE",
        seed: str | None = None,
    ) -> LiveBalatroSnapshot:
        params = {
            "deck": deck,
            "stake": stake,
        }

        if seed is not None:
            params["seed"] = seed

        return self.bridge.request(
            "start",
            params,
        )

    def restart_run(
        self,
        deck: str = "RED",
        stake: str = "WHITE",
        seed: str | None = None,
    ) -> LiveBalatroSnapshot:
        self.bridge.request("menu")
        return self.start_run(
            deck=deck,
            stake=stake,
            seed=seed,
        )

    def select_blind(self) -> LiveBalatroSnapshot:
        for attempt in range(self.select_retries + 1):
            try:
                return self.bridge.request("select")
            except BalatroBotRpcError as error:
                if (
                    not self._select_not_ready(error)
                    or attempt >= self.select_retries
                ):
                    raise

                if self.select_retry_delay > 0:
                    time.sleep(self.select_retry_delay)

        raise RuntimeError("unreachable")

    def skip_blind(self) -> LiveBalatroSnapshot:
        return self.bridge.request("skip")

    def cash_out(self) -> LiveBalatroSnapshot:
        return self.bridge.request("cash_out")

    def next_round(self) -> LiveBalatroSnapshot:
        return self.bridge.request("next_round")

    @classmethod
    def _select_not_ready(cls, error: BalatroBotRpcError) -> bool:
        message = str(error).lower()
        return any(
            fragment in message
            for fragment in cls.SELECT_NOT_READY_ERRORS
        )
