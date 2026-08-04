from framework.core.action import Action


class BalatroAction(Action):
    """
    Represents an action available in Balatro.
    """

    def __init__(
        self,
        name: str
    ):
        self.name = name


PLAY_HAND = BalatroAction("PLAY_HAND")
DISCARD_HAND = BalatroAction("DISCARD_HAND")
SELECT_CARD = BalatroAction("SELECT_CARD")
BUY_VOUCHER = BalatroAction("BUY_VOUCHER")
BUY_JOKER = BalatroAction("BUY_JOKER")
SELL_JOKER = BalatroAction("SELL_JOKER")
END_ROUND = BalatroAction("END_ROUND")