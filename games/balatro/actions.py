from framework.core.action import Action


class BalatroAction(Action):
    """
    Represents an action available in Balatro.
    """

    def __init__(
        self,
        action_type: str,
        target=None
    ):
        self.action_type = action_type
        self.target = target


    @property
    def name(self) -> str:
        return self.action_type


# General action types

PLAY_HAND = "PLAY_HAND"
DISCARD_HAND = "DISCARD_HAND"
SELECT_CARD = "SELECT_CARD"

BUY_VOUCHER = "BUY_VOUCHER"
BUY_JOKER = "BUY_JOKER"
SELL_JOKER = "SELL_JOKER"

END_ROUND = "END_ROUND"