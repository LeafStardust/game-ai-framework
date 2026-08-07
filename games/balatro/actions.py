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

END_ROUND = "END_ROUND"