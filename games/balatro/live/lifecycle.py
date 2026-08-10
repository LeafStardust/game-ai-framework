from games.balatro.live.balatrobot_bridge import BalatroBotBridge
from games.balatro.live.protocol import LiveBalatroSnapshot


class BalatroLiveLifecycle:

    def __init__(
        self,
        bridge: BalatroBotBridge,
    ):
        self.bridge = bridge

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
        return self.bridge.request("select")

    def skip_blind(self) -> LiveBalatroSnapshot:
        return self.bridge.request("skip")

    def cash_out(self) -> LiveBalatroSnapshot:
        return self.bridge.request("cash_out")

    def next_round(self) -> LiveBalatroSnapshot:
        return self.bridge.request("next_round")
