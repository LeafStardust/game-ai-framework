from games.balatro.live.balatrobot_bridge import BalatroBotBridge
from games.balatro.live.protocol import LiveBalatroSnapshot


class BalatroLiveLifecycle:

    def __init__(
        self,
        bridge: BalatroBotBridge,
    ):
        self.bridge = bridge

    def select_blind(self) -> LiveBalatroSnapshot:
        return self.bridge.request("select")

    def skip_blind(self) -> LiveBalatroSnapshot:
        return self.bridge.request("skip")

    def cash_out(self) -> LiveBalatroSnapshot:
        return self.bridge.request("cash_out")

    def next_round(self) -> LiveBalatroSnapshot:
        return self.bridge.request("next_round")
