from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class HitTheRoadJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is not None:
            if context.event.type == BalatroEventType.CARDS_DISCARDED:
                discarded_cards = context.event.cards or []

                self.x_mult += sum(
                    card.rank == "J"
                    for card in discarded_cards
                ) * 0.5

                return context

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context