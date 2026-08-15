from framework.core.action import Action


class BalatroAction(Action):

    def __init__(
        self,
        action_type: str,
        cards: list | None = None,
        target=None
    ):
        self.action_type = action_type
        self.cards = cards or []
        self.target = target


    @property
    def name(self) -> str:
        return self.action_type


    def copy(self):

        return BalatroAction(
            self.action_type,
            self.cards.copy(),
            self.target
        )


PLAY_CARDS = "PLAY_CARDS"
DISCARD_CARDS = "DISCARD_CARDS"
SELECT_CARDS = "SELECT_CARDS"

BUY_VOUCHER = "BUY_VOUCHER"
BUY_JOKER = "BUY_JOKER"
SELL_JOKER = "SELL_JOKER"
REORDER_JOKERS = "REORDER_JOKERS"
BUY_CONSUMABLE = "BUY_CONSUMABLE"
BUY_AND_USE_CONSUMABLE = "BUY_AND_USE_CONSUMABLE"
BUY_BOOSTER = "BUY_BOOSTER"
REFRESH_SHOP = "REFRESH_SHOP"
END_SHOP = "END_SHOP"
USE_CONSUMABLE = "USE_CONSUMABLE"

SELECT_PACK_CARD = "SELECT_PACK_CARD"
SKIP_BOOSTER = "SKIP_BOOSTER"

SELECT_BLIND = "SELECT_BLIND"
SKIP_BLIND = "SKIP_BLIND"
END_ROUND = "END_ROUND"
