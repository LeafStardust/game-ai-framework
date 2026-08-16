from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class YorickJoker(Joker):

    def __init__(self):
        self.discarded_cards = 0
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is not None:
            if context.event.type == BalatroEventType.CARDS_DISCARDED:
                self.discarded_cards += len(context.event.cards or [])

                while self.discarded_cards >= 23:
                    self.discarded_cards -= 23
                    self.x_mult += 1

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context
