from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class CastleJoker(Joker):

    def __init__(self, suit: str):
        self.suit = suit
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:

        if context.event is None:
            return context

        if context.event.type != BalatroEventType.CARDS_DISCARDED:
            return context

        matching_cards = sum(
            card.suit == self.suit
            for card in context.event.cards
        )

        self.chips += matching_cards * 3

        if context.score is not None:
            context.score.chips += self.chips

        return context